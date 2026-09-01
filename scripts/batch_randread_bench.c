#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/aio_abi.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

static long io_setup(unsigned nr_events, aio_context_t *ctxp)
{
	return syscall(__NR_io_setup, nr_events, ctxp);
}

static long io_destroy(aio_context_t ctx)
{
	return syscall(__NR_io_destroy, ctx);
}

static long io_submit(aio_context_t ctx, long nr, struct iocb **iocbpp)
{
	return syscall(__NR_io_submit, ctx, nr, iocbpp);
}

static long io_getevents(aio_context_t ctx, long min_nr, long nr, struct io_event *events,
			 struct timespec *timeout)
{
	return syscall(__NR_io_getevents, ctx, min_nr, nr, events, timeout);
}

static uint64_t now_ns(void)
{
	struct timespec ts;
	clock_gettime(CLOCK_MONOTONIC, &ts);
	return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

static uint64_t xorshift64(uint64_t *state)
{
	uint64_t x = *state;
	x ^= x << 13;
	x ^= x >> 7;
	x ^= x << 17;
	*state = x ? x : 0x9e3779b97f4a7c15ULL;
	return *state;
}

static int cmp_u64(const void *a, const void *b)
{
	uint64_t x = *(const uint64_t *)a;
	uint64_t y = *(const uint64_t *)b;
	return (x > y) - (x < y);
}

static uint64_t percentile(uint64_t *values, size_t n, double q)
{
	size_t idx;
	if (n == 0)
		return 0;
	idx = (size_t)ceil(q * (double)n);
	if (idx == 0)
		idx = 1;
	if (idx > n)
		idx = n;
	return values[idx - 1];
}

static uint64_t parse_size(const char *s)
{
	char *end = NULL;
	double value = strtod(s, &end);
	uint64_t scale = 1;

	if (end && *end) {
		switch (*end) {
		case 'k':
		case 'K':
			scale = 1024ULL;
			break;
		case 'm':
		case 'M':
			scale = 1024ULL * 1024ULL;
			break;
		case 'g':
		case 'G':
			scale = 1024ULL * 1024ULL * 1024ULL;
			break;
		default:
			scale = 1;
			break;
		}
	}

	return (uint64_t)(value * (double)scale);
}

static void usage(const char *prog)
{
	fprintf(stderr,
		"Usage: %s --filename DEV [--bs 4k] [--batch-size 16] [--size 6G]\n"
		"          [--runtime 20] [--warmup 3] [--seed 12345] [--gap-us 0]\n"
		"          [--csv OUT]\n",
		prog);
}

int main(int argc, char **argv)
{
	const char *filename = NULL;
	const char *csv_path = NULL;
	uint64_t bs = 4096;
	uint64_t range_size = 6ULL * 1024ULL * 1024ULL * 1024ULL;
	int batch_size = 16;
	int runtime_s = 20;
	int warmup_s = 3;
	int gap_us = 0;
	uint64_t seed = 12345;
	int fd = -1;
	aio_context_t ctx = 0;
	struct iocb *iocbs = NULL;
	struct iocb **iocb_ptrs = NULL;
	struct io_event *events = NULL;
	void **buffers = NULL;
	uint64_t *submit_ns = NULL;
	uint64_t *io_lat = NULL, *batch_lat = NULL;
	size_t io_count = 0, io_cap = 0, batch_count = 0, batch_cap = 0;
	uint64_t start_ns, warmup_end_ns, end_ns;
	uint64_t state;
	int rc = 1;

	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--filename") && i + 1 < argc) {
			filename = argv[++i];
		} else if (!strcmp(argv[i], "--bs") && i + 1 < argc) {
			bs = parse_size(argv[++i]);
		} else if (!strcmp(argv[i], "--batch-size") && i + 1 < argc) {
			batch_size = atoi(argv[++i]);
		} else if (!strcmp(argv[i], "--size") && i + 1 < argc) {
			range_size = parse_size(argv[++i]);
		} else if (!strcmp(argv[i], "--runtime") && i + 1 < argc) {
			runtime_s = atoi(argv[++i]);
		} else if (!strcmp(argv[i], "--warmup") && i + 1 < argc) {
			warmup_s = atoi(argv[++i]);
		} else if (!strcmp(argv[i], "--seed") && i + 1 < argc) {
			seed = strtoull(argv[++i], NULL, 0);
		} else if (!strcmp(argv[i], "--gap-us") && i + 1 < argc) {
			gap_us = atoi(argv[++i]);
		} else if (!strcmp(argv[i], "--csv") && i + 1 < argc) {
			csv_path = argv[++i];
		} else {
			usage(argv[0]);
			return 2;
		}
	}

	if (!filename || batch_size <= 0 || bs == 0 || range_size < bs) {
		usage(argv[0]);
		return 2;
	}

	fd = open(filename, O_RDONLY | O_DIRECT);
	if (fd < 0) {
		perror("open");
		goto out;
	}

	if (io_setup((unsigned)batch_size * 2, &ctx) < 0) {
		perror("io_setup");
		goto out;
	}

	iocbs = calloc((size_t)batch_size, sizeof(*iocbs));
	iocb_ptrs = calloc((size_t)batch_size, sizeof(*iocb_ptrs));
	events = calloc((size_t)batch_size, sizeof(*events));
	buffers = calloc((size_t)batch_size, sizeof(*buffers));
	submit_ns = calloc((size_t)batch_size, sizeof(*submit_ns));
	if (!iocbs || !iocb_ptrs || !events || !buffers || !submit_ns) {
		fprintf(stderr, "allocation failed\n");
		goto out;
	}

	for (int i = 0; i < batch_size; i++) {
		if (posix_memalign(&buffers[i], 4096, bs) != 0) {
			fprintf(stderr, "posix_memalign failed\n");
			goto out;
		}
		memset(buffers[i], 0, bs);
	}

	io_cap = 1024 * 1024;
	batch_cap = 65536;
	io_lat = malloc(io_cap * sizeof(*io_lat));
	batch_lat = malloc(batch_cap * sizeof(*batch_lat));
	if (!io_lat || !batch_lat) {
		fprintf(stderr, "latency allocation failed\n");
		goto out;
	}

	state = seed;
	start_ns = now_ns();
	warmup_end_ns = start_ns + (uint64_t)warmup_s * 1000000000ULL;
	end_ns = warmup_end_ns + (uint64_t)runtime_s * 1000000000ULL;

	while (now_ns() < end_ns) {
		uint64_t batch_submit_ns = now_ns();
		int submitted = 0;
		int completed = 0;
		int measured = batch_submit_ns >= warmup_end_ns;

		memset(iocbs, 0, (size_t)batch_size * sizeof(*iocbs));
		for (int i = 0; i < batch_size; i++) {
			uint64_t blocks = range_size / bs;
			uint64_t block = xorshift64(&state) % blocks;
			uint64_t offset = block * bs;

			iocbs[i].aio_fildes = fd;
			iocbs[i].aio_lio_opcode = IOCB_CMD_PREAD;
			iocbs[i].aio_buf = (uint64_t)buffers[i];
			iocbs[i].aio_nbytes = bs;
			iocbs[i].aio_offset = offset;
			iocbs[i].aio_data = (uint64_t)i;
			iocb_ptrs[i] = &iocbs[i];
			submit_ns[i] = batch_submit_ns;
		}

		while (submitted < batch_size) {
			long ret = io_submit(ctx, batch_size - submitted, &iocb_ptrs[submitted]);
			if (ret < 0) {
				errno = -ret;
				perror("io_submit");
				goto out;
			}
			submitted += (int)ret;
		}

		while (completed < batch_size) {
			long ret = io_getevents(ctx, 1, batch_size - completed, events, NULL);
			uint64_t complete_ns = now_ns();
			if (ret < 0) {
				errno = -ret;
				perror("io_getevents");
				goto out;
			}
			for (long i = 0; i < ret; i++) {
				int idx = (int)events[i].data;
				if (events[i].res < 0) {
					errno = (int)-events[i].res;
					perror("aio read");
					goto out;
				}
				if ((uint64_t)events[i].res != bs) {
					fprintf(stderr, "short read: %lld\n", (long long)events[i].res);
					goto out;
				}
				if (measured) {
					if (io_count == io_cap) {
						io_cap *= 2;
						io_lat = realloc(io_lat, io_cap * sizeof(*io_lat));
						if (!io_lat) {
							fprintf(stderr, "latency realloc failed\n");
							goto out;
						}
					}
					io_lat[io_count++] = complete_ns - submit_ns[idx];
				}
			}
			completed += (int)ret;
		}

		if (measured) {
			uint64_t batch_done_ns = now_ns();
			if (batch_count == batch_cap) {
				batch_cap *= 2;
				batch_lat = realloc(batch_lat, batch_cap * sizeof(*batch_lat));
				if (!batch_lat) {
					fprintf(stderr, "batch latency realloc failed\n");
					goto out;
				}
			}
			batch_lat[batch_count++] = batch_done_ns - batch_submit_ns;
		}

		if (gap_us > 0)
			usleep((useconds_t)gap_us);
	}

	qsort(io_lat, io_count, sizeof(*io_lat), cmp_u64);
	qsort(batch_lat, batch_count, sizeof(*batch_lat), cmp_u64);

	{
		uint64_t sum = 0;
		double mean = 0.0, variance = 0.0, iops, bw_mib_s;
		FILE *csv = stdout;

		for (size_t i = 0; i < io_count; i++)
			sum += io_lat[i];
		mean = io_count ? (double)sum / (double)io_count : 0.0;
		for (size_t i = 0; i < io_count; i++) {
			double d = (double)io_lat[i] - mean;
			variance += d * d;
		}
		variance = io_count > 1 ? variance / (double)(io_count - 1) : 0.0;
		iops = (double)io_count / (double)runtime_s;
		bw_mib_s = iops * (double)bs / 1024.0 / 1024.0;

		if (csv_path) {
			csv = fopen(csv_path, "w");
			if (!csv) {
				perror("fopen csv");
				goto out;
			}
		}

		fprintf(csv,
			"bs,batch_size,gap_us,runtime_s,warmup_s,total_ios,total_batches,iops,bw_mib_s,"
			"io_mean_us,io_stddev_us,io_p50_us,io_p90_us,io_p99_us,io_p999_us,io_p9999_us,io_max_us,"
			"batch_mean_us,batch_p50_us,batch_p90_us,batch_p99_us,batch_p999_us,batch_max_us\n");
		fprintf(csv,
			"%llu,%d,%d,%d,%d,%zu,%zu,%.2f,%.2f,"
			"%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,"
			"%.2f,%.2f,%.2f,%.2f,%.2f,%.2f\n",
			(unsigned long long)bs, batch_size, gap_us, runtime_s, warmup_s,
			io_count, batch_count, iops, bw_mib_s,
			mean / 1000.0, sqrt(variance) / 1000.0,
			(double)percentile(io_lat, io_count, 0.50) / 1000.0,
			(double)percentile(io_lat, io_count, 0.90) / 1000.0,
			(double)percentile(io_lat, io_count, 0.99) / 1000.0,
			(double)percentile(io_lat, io_count, 0.999) / 1000.0,
			(double)percentile(io_lat, io_count, 0.9999) / 1000.0,
			io_count ? (double)io_lat[io_count - 1] / 1000.0 : 0.0,
			batch_count ? ((double)({ uint64_t s = 0; for (size_t i = 0; i < batch_count; i++) s += batch_lat[i]; s; }) / (double)batch_count) / 1000.0 : 0.0,
			(double)percentile(batch_lat, batch_count, 0.50) / 1000.0,
			(double)percentile(batch_lat, batch_count, 0.90) / 1000.0,
			(double)percentile(batch_lat, batch_count, 0.99) / 1000.0,
			(double)percentile(batch_lat, batch_count, 0.999) / 1000.0,
			batch_count ? (double)batch_lat[batch_count - 1] / 1000.0 : 0.0);

		if (csv_path)
			fclose(csv);
	}

	rc = 0;

out:
	if (ctx)
		io_destroy(ctx);
	if (fd >= 0)
		close(fd);
	if (buffers) {
		for (int i = 0; i < batch_size; i++)
			free(buffers[i]);
	}
	free(buffers);
	free(iocbs);
	free(iocb_ptrs);
	free(events);
	free(submit_ns);
	free(io_lat);
	free(batch_lat);
	return rc;
}
