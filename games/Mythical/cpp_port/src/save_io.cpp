#include "save_io.hpp"

#include <fstream>
#include <iterator>

namespace mythical::port {

bool save_to_file(const SaveState& state, const std::string& path) {
    const auto bytes = pack_save(state);
    std::ofstream f(path, std::ios::binary);
    if (!f) return false;
    f.write(reinterpret_cast<const char*>(bytes.data()), static_cast<std::streamsize>(bytes.size()));
    return static_cast<bool>(f);
}

SaveResult load_from_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return SaveResult();
    std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(f)),
                                      std::istreambuf_iterator<char>());
    return unpack_save(bytes);
}

}  // namespace mythical::port
