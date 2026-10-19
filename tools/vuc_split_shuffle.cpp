// Separate NBR/vector placements using the same graph-edge block objective as
// DiskANN_cpp/src/disk_utils.cpp::compute_block_shuffled_order.
// Logical IDs stay unchanged; only record placement is permuted.
#define main nbr_layout_legacy_main
#include "nbr_only_block_shuffle.cpp"
#undef main
int main(int argc, char** argv) {
    try {
        if (argc != 6) throw std::runtime_error("usage: vuc_split_shuffle base.fbin graph.mem.index out_dir iterations gain_threshold");
        const auto n = read_base_count(argv[1]);
        uint32_t width, medoid; uint64_t frozen;
        auto graph = read_graph(argv[2], n, width, medoid, frozen);
        if (width > 64) throw std::runtime_error("VUC requires graph width <=64");
        std::filesystem::create_directories(argv[3]);
        for (uint32_t capacity : {15u, 8u}) {
            auto order = compute_order(graph, capacity, std::stoul(argv[4]), std::stod(argv[5]));
            std::vector<uint32_t> inverse(n);
            for (uint32_t i=0; i<n; ++i) inverse[order[i]]=i;
            const std::string prefix=std::string(argv[3]) + (capacity==15 ? "/nbr" : "/vector");
            write_map(prefix+".old_to_new.bin", inverse);
            write_map(prefix+".new_to_old.bin", order);
        }
    } catch(const std::exception& e) { std::cerr<<e.what()<<'\n'; return 1; }
}
