import json
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

import yaml
from .profiles import ProjectProfile, iter_profiles
from .task_distributer import TaskDistributer


KNOWN_DOMAIN_OVERRIDES = {
    "apache-httpd": "web-server",
    "binutils": "binary-tools",
    "bluez": "bluetooth",
    "brotli": "compression",
    "bzip2": "compression",
    "cairo": "graphics",
    "c-ares": "dns",
    "cfengine": "configuration-management",
    "clib": "utility-library",
    "cmark": "markup/markdown",
    "cpuinfo": "system-info",
    "cpython3": "language-runtime/python",
    "cryptofuzz": "crypto/fuzz-harness",
    "dbus-broker": "ipc/message-bus",
    "dnsmasq": "dns/dhcp",
    "elfutils": "binary-tools",
    "envoy": "proxy/load-balancer",
    "esp-v2": "proxy/api-gateway",
    "firefox": "browser",
    "flex": "parser-generator",
    "gdk-pixbuf": "image-processing",
    "giflib": "image-processing",
    "git": "version-control",
    "gnupg": "crypto/pgp",
    "gpac": "multimedia/container",
    "gpsd": "gps",
    "gss-ntlmssp": "auth/protocol",
    "h3": "http/http3",
    "haproxy": "proxy/load-balancer",
    "hdf5": "scientific-io",
    "hiredis": "database-client/redis",
    "hoextdown": "markup/markdown",
    "hpn-ssh": "ssh",
    "http-parser": "http/parser",
    "hwloc": "system-topology",
    "inchi": "cheminformatics",
    "inih": "config-parser",
    "jq": "json/cli",
    "kamailio": "voip/sip",
    "keystone": "assembler",
    "lcms": "color-management",
    "libdwarf": "debug-info",
    "libevent": "network/event-loop",
    "libfuse": "filesystem",
    "libgit2": "version-control",
    "libhtp": "http/parser",
    "libiec61850": "industrial-control",
    "libldac": "audio/bluetooth",
    "libmodbus": "industrial-control",
    "libpcap": "network/capture",
    "libpg_query": "database/parser",
    "librdkafka": "messaging/streaming",
    "libressl": "crypto/tls",
    "libssh": "ssh",
    "libteken": "terminal",
    "libtsm": "terminal",
    "libucl": "config",
    "libunwind": "debug-info",
    "libyaml": "serialization/yaml",
    "libyang": "network/config",
    "lighttpd": "web-server",
    "llhttp": "http/parser",
    "lua": "language-runtime/lua",
    "lzo": "compression",
    "mariadb": "database/sql",
    "md4c": "markup/markdown",
    "memcached": "cache",
    "mongoose": "web-server/embedded",
    "mpg123": "audio/decoder",
    "mruby": "language-runtime/ruby",
    "nginx": "web-server",
    "ntpsec": "time-sync",
    "numactl": "system/numa",
    "openssh": "ssh",
    "openvpn": "vpn",
    "opusfile": "audio/codec",
    "oss-fuzz-example": "example",
    "ostree": "system/update",
    "pacemaker": "cluster-management",
    "pidgin": "messaging/IM",
    "plan9port": "os/userland",
    "postfix": "email/smtp",
    "postgresql": "database/sql",
    "protobuf-c": "serialization/protobuf",
    "pycryptodome": "crypto",
    "pyodbc": "database/odbc",
    "quiche": "quic/http3",
    "quickjs": "language-runtime/js",
    "skcms": "color-management",
    "sound-open-firmware": "audio/firmware",
    "spidermonkey-ufi": "language-runtime/js",
    "sqlite3": "database/sql",
    "suricata": "ids/ips",
    "tensorflow-serving": "ml/serving",
    "tensorflow": "ml/framework",
    "tidy-html5": "html/parser",
    "unbound": "dns",
    "usrsctp": "transport/sctp",
    "vlc": "multimedia/player",
    "vulkan-loader": "graphics/gpu",
    "w3m": "browser/text",
    "wasm3": "language-runtime/wasm",
    "wazuh": "security/siem",
    "wuffs": "image-processing",
    "xmlsec": "xml/security",
    "yajl-ruby": "json/binding",
    "zlib": "compression",
    "zydis": "disassembly",

    # toolchain / binary utilities
    "llvm": "binary-tools",
    "llvm_libcxx": "binary-tools",
    "llvm_libcxxabi": "binary-tools",
    "radare2": "binary-tools",
    "capstone": "disassembly",
    "file": "filesystem",          # maps to coarse 'metadata'
    "e2fsprogs": "filesystem",
    "unicorn": "binary-tools",
    "lldb-eval": "debug-info",

    # media (image/audio/video/graphics)
    "ffmpeg": "multimedia",
    "vlc": "multimedia/player",    # already above, just keep that
    "imagemagick": "image-processing",
    "graphicsmagick": "image-processing",
    "libpng": "image-processing",
    "libjpeg-turbo": "image-processing",
    "libtiff": "image-processing",
    "libwebp": "image-processing",
    "libheif": "image-processing",
    "flac": "audio/codec",
    "vorbis": "audio/codec",
    "opus": "audio/codec",
    "wavpack": "audio/codec",
    "faad2": "audio/codec",
    "libmpeg2": "video/codec",

    # document / markup / PDF / XML / JSON
    "xpdf": "document",            # coarse: document
    "poppler": "document",
    "mupdf": "document",
    "libxml2": "xml",
    "expat": "xml",
    "yaml-cpp": "yaml",
    "json-c": "json",
    "jsoncpp": "json",
    "jsoncons": "json",
    "pugixml": "xml",
    "tidy-html5": "html/parser",   # already present above

    # archive / compression
    "libarchive": "compression",
    "xz": "compression",
    "zstd": "compression",
    "zip": "compression",
    "unrar": "compression",
    "upx": "compression",

    # crypto / hash / security
    "openssl": "crypto/tls",
    "boringssl": "crypto/tls",
    "gnutls": "crypto/tls",
    "wolfssl": "crypto/tls",
    "bearssl": "crypto/tls",
    "libsodium": "crypto",
    "mbedtls": "crypto/tls",
    "wolfmqtt": "crypto",          # secure messaging-ish
    "rnp": "crypto/pgp",
    "tpm2": "crypto",
    "tpm2-tss": "crypto",

    # network / protocol / servers / clients
    "curl": "http",                # coarse: network
    "wget": "http",
    "wget2": "http",
    "nghttp2": "http",
    "trafficserver": "proxy/load-balancer",
    "varnish": "proxy/load-balancer",
    "wireshark": "network/capture",
    "pcapplusplus": "network/capture",
    "systemd": "network",
    "networkmanager": "network",
    "openvswitch": "network",
    "osquery": "network",

    # database / storage
    "duckdb": "database/sql",
    "mysql-server": "database/sql",
    "rocksdb": "database/storage",

    # ML / numeric / scientific
    "tensorflow": "ml/framework",
    "xnnpack": "ml/framework",
    "eigen": "scientific-io",

    # metadata / helper utilities
    "exiv2": "filesystem",         # file metadata → coarse metadata
    "libexif": "filesystem",
    "libvips": "image-processing",
    "sleuthkit": "filesystem",

    "abseil-cpp": "utility-library",
    "ada-url": "http/parser",
    "alembic": "graphics/3d",
    "ampproject": "web-framework",
    "angle": "graphics/gpu",
    "args": "utility-library",
    "arrow": "serialization/columnar",
    "aspell": "text/spellcheck",
    "assimp": "graphics/3d",
    "astc-encoder": "image-processing",
    "augeas": "config",
    "avahi": "network/service-discovery",
    "bad_example": "compression",
    "bazel-rules-fuzzing-test": "example",
    "bc-gh": "math/bignum",
    "behaviortreecpp": "framework/behavior-tree",
    "bignum-fuzzer": "crypto",
    "bios-bmc-smm-error-logger": "system/firmware",
    "bitcoin-core": "crypto/blockchain",
    "bloaty": "binary-tools",
    "bls-signatures": "crypto/signature",
    "boost-beast": "http",
    "boost": "utility-library",
    "botan": "crypto",
    "brpc": "rpc/framework",
    "brunsli": "compression",
    "c-blosc": "compression",
    "c-blosc2": "compression",
    "capnproto": "serialization",
    "casync": "filesystem",
    "cctz": "datetime",
    "cel-cpp": "config/expr",
    "cel-go": "config/expr",
    "cifuzz-example": "example",
    "circl": "crypto",
    "civetweb": "web-server/embedded",
    "clamav": "security/antivirus",
    "clickhouse": "database/sql",
    "cmake": "build-system",
    "connectedhomeip": "iot/protocol",
    "coturn": "voip/sip",
    "cppcheck": "analysis/static",
    "cppitertools": "utility-library",
    "croaring": "data-structure",
    "crow": "web-framework",
    "cryptofuzz": "crypto/fuzz-harness",
    "cups-filters": "print/spooler",
    "cups": "print/spooler",
    "cura-engine": "graphics/3d-print",
    "cxxopts": "utility-library",
    "cyclonedds": "messaging/dds",
    "dart": "language-runtime/dart",
    "date": "datetime",
    "dav1d": "video/codec",
    "dlplibs": "utility-library",
    "dng_sdk": "image-processing",
    "double-conversion": "numeric/format",
    "dovecot": "email/imap",
    "dpp": "messaging/IM",
    "draco": "graphics/3d",
    "easywsclient": "http",
    "ecc-diff-fuzzer": "crypto",
    "edk2": "firmware",
    "espeak-ng": "audio/tts",
    "example": "example",
    "exprtk": "math/expression",
    "fast-dds": "messaging/dds",
    "fast_float": "numeric/format",
    "ffms2": "multimedia",
    "fftw3": "numeric/fft",
    "fio": "benchmark/io",
    "firefox": "browser",
    "firestore": "database/nosql",
    "flatbuffers": "serialization/binary",
    "fluent-bit": "logging",
    "fmt": "logging",
    "freeimage": "image-processing",
    "freeradius": "auth/radius",
    "freerdp": "remote-desktop/rdp",
    "freetype2": "fonts",
    "fribidi": "text/bidi",
    "frr": "network/routing",
    "fuzzing-puzzles": "example",
    "fuzztest-example": "example",
    "fwupd": "system/update",
    "geos": "scientific-io/gis",
    "gfwx": "scientific-io/gis",
    "glaze": "json/parser",
    "glib": "utility-library",
    "glog": "logging",
    "glslang": "graphics/shader",
    "gnucobol": "language-runtime/cobol",
    "graphicsfuzz-spirv": "graphics/shader",
    "graphicsmagick": "image-processing",
    "grok": "image-processing",
    "guetzli": "image-processing",
    "halide": "image-processing",
    "harfbuzz": "fonts",
    "hermes": "language-runtime/js",
    "hostap": "network/wifi",
    "htslib": "bioinformatics",
    "hunspell": "text/spellcheck",
    "icu": "text/encoding",
    "igraph": "graph/algorithms",
    "immer": "data-structure/persistent",
    "iroha": "crypto/blockchain",
    "irssi": "messaging/IM",
    "iverilog": "hdl/simulator",
    "janet": "language-runtime/janet",
    "jansson": "json/parser",
    "janus-gateway": "voip/webrtc",
    "java-example": "example",
    "jbig2dec": "image-processing",
    "jerryscript": "language-runtime/js",
    "jsc": "language-runtime/js",
    "jwt-verify-lib": "auth/jwt",
    "kde-thumbnailers": "image-processing",
    "kea": "network/dhcp",
    "kmime": "email/mime",
    "krb5": "auth/kerberos",
    "lame": "audio/codec",
    "leptonica": "image-processing",
    "libaom": "video/codec",
    "libass": "subtitle/rendering",
    "libavif": "image-processing",
    "libbpf": "system/ebpf",
    "libcacard": "auth/smartcard",
    "libcbor": "serialization/cbor",
    "libcoap": "iot/protocol",
    "libconfig": "config",
    "libcue": "audio/metadata",
    "libcups": "print/spooler",
    "libecc": "crypto",
    "libfido2": "auth/fido2",
    "libgd": "image-processing",
    "libhevc": "video/codec",
    "libical": "calendar",
    "libidn": "dns/idn",
    "libidn2": "dns/idn",
    "libigl": "graphics/3d",
    "libjxl": "image-processing",
    "liblouis": "accessibility/braille",
    "liboqs": "crypto/post-quantum",
    "libphonenumber": "telecom/phone-number",
    "libplist": "serialization/plist",
    "libpng-proto": "image-processing",
    "libprotobuf-mutator": "serialization/protobuf",
    "libpsl": "dns",
    "libraw": "image-processing",
    "librawspeed": "image-processing",
    "libredwg": "cad/dwg",
    "libreoffice": "document",
    "libsass": "css/parser",
    "libsndfile": "audio/codec",
    "libsoup": "http/client",
    "libspdm": "security/spdm",
    "libspectre": "document/postscript",
    "libsrtp": "crypto",
    "libstdcpp": "toolchain",
    "libtasn1": "crypto/x509",
    "libteken": "terminal",
    "libtheora": "video/codec",
    "libtorrent": "torrent/p2p",
    "libultrahdr": "image-processing",
    "libusb": "usb",
    "libvnc": "remote-desktop/vnc",
    "libvpx": "video/codec",
    "libwebsockets": "http",
    "libxls": "document/spreadsheet",
    "libxlsxwriter": "document/spreadsheet",
    "libxslt": "xml/parser",
    "libyal": "filesystem",
    "libyuv": "video/processing",
    "libzmq": "messaging/broker",
    "llamacpp": "ml/framework",
    "lldpd": "network",
    "lwan": "web-server",
    "lxc": "container",
    "lzo": "compression",
    "magic-enum": "utility-library",
    "mapserver": "scientific-io/gis",
    "mdbtools": "database/sql",
    "mercurial": "version-control",
    "meshoptimizer": "graphics/3d",
    "mfcmapi": "email/mapi",
    "miniz": "compression",
    "monero": "crypto/blockchain",
    "mosh": "ssh",
    "mosquitto": "messaging/broker",
    "mpv": "multimedia/player",
    "muduo": "network",
    "muparser": "math/expression",
    "nanopb": "serialization/protobuf",
    "nccl": "ml/framework",
    "ndpi": "network/traffic-analysis",
    "neomutt": "email/imap",
    "nestegg": "multimedia/container",
    "nettle": "crypto",
    "ninja": "build-system",
    "njs": "language-runtime/js",
    "nodejs": "language-runtime/js",
    "nokogiri": "xml/parser",
    "nss": "crypto/tls",
    "ntp": "time-sync",
    "num-bigint": "math/bignum",
    "oatpp": "web-framework",
    "ogre": "graphics/3d",
    "onednn": "ml/framework",
    "open5gs": "network/mobile-core",
    "open62541": "industrial-control",
    "openbabel": "cheminformatics",
    "opencensus-cpp": "observability/tracing",
    "opencv": "image-processing",
    "opendds": "messaging/dds",
    "opendnp3": "industrial-control",
    "openexr": "image-processing",
    "openh264": "video/codec",
    "opennavsurf-bag": "scientific-io/gis",
    "opensc": "auth/smartcard",
    "opensips": "voip/sip",
    "openslide": "image-processing",
    "openthread": "iot/protocol",
    "openweave": "iot/protocol",
    "ots": "fonts",
    "p11-kit": "auth/smartcard",
    "pcl": "scientific-io/gis",
    "pcre2": "regex",
    "perfetto": "observability/tracing",
    "pffft": "numeric/fft",
    "phmap": "data-structure",
    "php": "language-runtime/php",
    "pidgin": "messaging/IM",
    "piex": "image-processing",
    "pigweed": "embedded/framework",
    "pistache": "web-framework",
    "pjsip": "voip/sip",
    "poco": "utility-library",
    "postgis": "database/gis",
    "postgresql": "database/sql",
    "proftpd": "ftp/server",
    "proj4": "scientific-io/gis",
    "pupnp": "network/upnp",
    "python3-libraries": "language-runtime/python",
    "qemu": "virtualization",
    "qpid-proton": "messaging/broker",
    "qs": "http/parser",
    "qt": "gui/framework",
    "quantlib": "finance/quant",
    "qubes-os": "os/security",
    "rabbitmq-c": "messaging/broker",
    "rauc": "system/update",
    "rdkit": "cheminformatics",
    "re2": "regex",
    "readstat": "data/statistics",
    "relic": "crypto",
    "resiprocate": "voip/sip",
    "s2geometry": "scientific-io/gis",
    "s2opc": "industrial-control",
    "samba": "filesystem/network-share",
    "selinux": "security/selinux",
    "sentencepiece": "nlp/tokenizer",
    "serenity": "os/kernel",
    "simd": "image-processing",
    "simdutf": "text/encoding",
    "snappy": "compression",
    "solidity": "crypto/blockchain",
    "spdk": "storage/nvme",
    "spdlog": "logging",
    "speex": "audio/codec",
    "spice-usbredir": "remote-desktop/usb",
    "spicy": "language-runtime",
    "spidermonkey-ufi": "language-runtime/js",
    "spidermonkey": "language-runtime/js",
    "spirv-cross": "graphics/shader",
    "spirv-tools": "graphics/shader",
    "sql-parser": "database/sql",
    "sqlite3": "database/sql",
    "stb": "image-processing",
    "strongswan": "vpn",
    "sudoers": "os/security",
    "tcmalloc": "memory/allocator",
    "tdengine": "database/time-series",
    "tesseract-ocr": "image-ocr",
    "thrift": "rpc/framework",
    "tink-cc": "crypto",
    "tinygltf": "graphics/3d",
    "tinyobjloader": "graphics/3d",
    "tinysparql": "database/sparql",
    "tinyusb": "usb",
    "tmux": "terminal",
    "tor": "network/anon",
    "tremor": "audio/codec",
    "unit": "web-server",
    "uriparser": "http/parser",
    "usbguard": "security/usb",
    "utf8proc": "text/encoding",
    "util-linux": "os/utils",
    "uwebsockets": "http",
    "v8": "language-runtime/js",
    "vulnerable-project": "example",
    "wabt": "language-runtime/wasm",
    "wamr": "language-runtime/wasm",
    "wasmedge": "language-runtime/wasm",
    "woff2": "fonts",
    "wpantund": "iot/protocol",
    "wt": "web-framework",
    "wxwidgets": "gui/framework",
    "xbps": "package-manager",
    "xen": "virtualization",
    "xerces-c": "xml/parser",
    "xnu": "os/kernel",
    "xpdf": "document/pdf",
    "xs": "language-runtime/js",
    "yara": "security/malware",
    "yoga": "gui/layout",
    "zeek": "ids/ips",
    "znc": "messaging/IM",
    "zopfli": "compression",

}


DOMAINS_YAML = Path(__file__).with_name("domains.yml")

# Only C / C++ source + headers
C_LANG_WHITELIST = {
    "C",
    "C++",
    "C/C++ Header",
}


class DomainMapper:
    """
    Handles domain mapping and inference for OSS-Fuzz projects.
    """

    def __init__(
        self,
        domains_yaml: Path = DOMAINS_YAML,
        overrides: Optional[dict] = None,
    ) -> None:
        self.domains_yaml = domains_yaml
        self.overrides = overrides or KNOWN_DOMAIN_OVERRIDES
        self._coarse_map_cache: Optional[dict] = None

    # --- Coarse map loading / lookup ------------------------------------
    def load_coarse_map(self) -> dict:
        if self._coarse_map_cache is not None:
            return self._coarse_map_cache

        try:
            with self.domains_yaml.open("r") as f:
                data = yaml.safe_load(f) or {}
            self._coarse_map_cache = data.get("coarse_map", {})
        except Exception as e:
            print(f"[domain] WARNING: failed to load {self.domains_yaml}: {e}")
            self._coarse_map_cache = {}

        return self._coarse_map_cache

    def map_fine_to_coarse(self, fine_label: str) -> str:
        """
        Map a fine-grained label like 'http/parser' or 'compression'
        to a coarse domain id like 'network', 'archive', etc.
        """
        if not fine_label:
            return "unknown"

        coarse_map = self.load_coarse_map()

        # Exact match
        if fine_label in coarse_map:
            return coarse_map[fine_label]

        # Prefix match (before '/')
        prefix = fine_label.split("/", 1)[0]
        if prefix in coarse_map:
            return coarse_map[prefix]

        # Fallback bucket
        return coarse_map.get("other", "unknown")

    # --- Heuristics for fine labels --------------------------------------

    def guess_fine_label_from_name(self, project: str) -> Optional[str]:
        """
        Infer a fine_label from the OSS-Fuzz project name using simple string rules.
        This is where we cover the *rest* of the 557 projects.
        """
        name = project.lower()

        # --- toolchain / compilers / linkers ---
        if any(x in name for x in ["binutils", "objdump", "nm", "addr2line", "readelf"]):
            return "binary-tools"
        if "llvm" in name or "clang" in name:
            return "binary-tools"
        if "assembler" in name or "keystone" in name:
            return "assembler"
        if any(x in name for x in ["gdb", "lldb"]):
            return "debug-info"

        # --- media / image / audio / video ---
        if any(x in name for x in ["png", "jpeg", "tiff", "gif", "image", "magick", "pixbuf", "webp"]):
            return "image-processing"
        if any(x in name for x in ["ffmpeg", "xvid", "vorbis", "opus", "flac", "wavpack", "mpg123", "audio", "codec"]):
            return "audio/codec"
        if "gstreamer" in name or "vlc" in name:
            return "multimedia/player"
        if "gpac" in name:
            return "multimedia/container"
        if any(x in name for x in ["cairo", "skia", "vulkan", "opengl"]):
            return "graphics"

        # --- document / markup / json / xml / pdf ---
        if "libxml2" in name or "xmlsec" in name or "xml" in name:
            return "xml/parser"
        if any(x in name for x in ["json", "yajl", "rapidjson", "jsoncpp", "jsonnet"]):
            return "json/parser"
        if any(x in name for x in ["markdown", "cmark", "md4c"]):
            return "markup/markdown"
        if any(x in name for x in ["pdf", "poppler", "xpdf", "ghostscript"]):
            return "pdf/parser"
        if "html" in name or "tidy-html5" in name:
            return "html/parser"

        # --- archive / compression ---
        if any(x in name for x in ["zlib", "zstd", "lz4", "xz", "bzip2", "brotli", "zip", "unzip", "minizip"]):
            return "compression"
        if "archive" in name or "tar" in name or "cpio" in name:
            return "archiving"

        # --- crypto / hashing / tls ---
        if any(x in name for x in ["openssl", "boringssl", "libressl", "gnutls", "mbedtls", "wolfssl"]):
            return "crypto/tls"
        if any(x in name for x in ["crypto", "hash", "sha", "md5", "blake", "sodium", "libsodium", "bearssl"]):
            return "crypto"
        if "gnupg" in name or "pgp" in name:
            return "crypto/pgp"

        # --- network / dns / http / ssh / vpn / protocols ---
        if any(x in name for x in ["curl", "wget", "nghttp2", "http", "h2o", "envoy"]):
            return "http/client"
        if any(x in name for x in ["bind", "unbound", "dnsmasq", "dns"]):
            return "dns"
        if any(x in name for x in ["ssh", "openssh", "dropbear", "libssh"]):
            return "ssh"
        if "openvpn" in name or "wireguard" in name:
            return "vpn"
        if any(x in name for x in ["quic", "h3", "quiche", "msquic"]):
            return "quic/http3"
        if "suricata" in name or "snort" in name:
            return "ids/ips"
        if "pcap" in name or "libpcap" in name:
            return "network/capture"

        # --- databases / storage ---
        if any(x in name for x in ["sqlite", "postgres", "mariadb", "mysql", "duckdb", "rocksdb", "leveldb"]):
            return "database/sql"

        # --- metadata / file-info ---
        if "exiv2" in name or "libexif" in name or name == "file":
            return "metadata/file-info"

        # --- ML / scientific ---
        if "tensorflow" in name or "onnx" in name:
            return "ml/framework"
        if any(x in name for x in ["hdf5", "netcdf", "gdal", "matio"]):
            return "scientific-io"

        # fallback: unknown
        return None

    # --- High-level domain inference ------------------------------------
    def infer_domain(self, profile: ProjectProfile) -> tuple[str, Optional[str]]:
        """
        Infer (coarse_domain, fine_label) for this project.
        fine_label is what overrides / heuristics produce.
        coarse_domain is mapped via domains.yml coarse_map.
        """
        # 1) Explicit override wins
        fine_label = self.overrides.get(profile.project)

        # 2) If no override, try heuristic from project name
        if not fine_label:
            fine_label = self.guess_fine_label_from_name(profile.project)

        # 3) If still nothing, fall back to existing profile.domain (if any)
        if not fine_label and profile.domain and profile.domain.lower() not in ("unknown", "null"):
            fine_label = profile.domain

        # 4) If still unknown, return unknown
        if not fine_label:
            return "unknown", None

        # 5) Map fine -> coarse using domains.yml
        coarse = self.map_fine_to_coarse(fine_label)
        return coarse, fine_label


_DEFAULT_DOMAIN_MAPPER: Optional[DomainMapper] = None


def _get_default_domain_mapper() -> DomainMapper:
    global _DEFAULT_DOMAIN_MAPPER
    if _DEFAULT_DOMAIN_MAPPER is None:
        _DEFAULT_DOMAIN_MAPPER = DomainMapper(domains_yaml=DOMAINS_YAML, overrides=KNOWN_DOMAIN_OVERRIDES)
    return _DEFAULT_DOMAIN_MAPPER


class ProfileAugmenter:
    """
    Handles repository cloning, LOC computation, and profile augmentation.
    """

    def __init__(self, clone_root: Path, domain_mapper: Optional[DomainMapper] = None) -> None:
        self.clone_root = clone_root
        self.domain_mapper = domain_mapper or _get_default_domain_mapper()

    # --- Repo management -------------------------------------------------
    def clone_repo_if_needed(self, main_repo: str, target_dir: Path) -> None:
        if target_dir.is_dir():
            return
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        print(f"[clone] git clone {main_repo} -> {target_dir}")
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", main_repo, str(target_dir)],
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[clone] WARNING: git clone failed for {main_repo}: {e}")

    # --- LOC computation using cloc -------------------------------------
    def _compute_loc_with_cloc(self, repo_dir: Path) -> Optional[int]:
        """
        Use cloc to compute LOC for C/C++ sources and headers only.
        Returns total LOC (int) or None if cloc fails.
        """
        try:
            proc = subprocess.run(
                [
                    "cloc",
                    "--json",
                    "--include-lang=C,C++,C/C++ Header",
                    ".",
                ],
                cwd=str(repo_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            data = json.loads(proc.stdout)

            total = 0
            for lang, info in data.items():
                # cloc metadata keys are not dicts; skip those
                if not isinstance(info, dict):
                    continue
                if lang not in C_LANG_WHITELIST:
                    continue
                code = info.get("code")
                if isinstance(code, int):
                    total += code

            return total
        except Exception as e:
            print(f"[loc] cloc failed in {repo_dir}: {e}")
            return None

    def compute_loc(self, repo_dir: Path) -> int:
        """
        Compute C/C++ LOC using cloc only.
        If cloc fails, return 0 (no slow Python fallback).
        """
        loc = self._compute_loc_with_cloc(repo_dir)
        if loc is None:
            return 0
        return loc

    # --- High-level profile augmentation --------------------------------
    def augment(self, profile: ProjectProfile) -> ProjectProfile:
        main_repo = profile.main_repo
        has_repo = bool(main_repo) and str(main_repo).lower() not in ("null", "")

        # --- LOC: only compute if missing or clearly invalid ---
        if has_repo:
            repo_dir = self.clone_root / profile.project
            self.clone_repo_if_needed(profile.main_repo, repo_dir)

            loc_val = profile.loc
            if loc_val is None or (isinstance(loc_val, int) and loc_val <= 0):
                loc_val = self.compute_loc(repo_dir)
        else:
            loc_val = 0
        
        # --- Domain inference (this already respects existing domain) ---
        coarse_domain, fine_label = self.domain_mapper.infer_domain(profile)

        profile.loc = loc_val
        profile.domain = coarse_domain
        if hasattr(profile, "domain_label"):
            profile.domain_label = fine_label

        print(
            f"[augment] {profile.project}: loc={loc_val}, "
            f"domain={coarse_domain}, fine_label={fine_label}"
        )
        return profile


# ----------------------------------------------------------------------
# Backwards-compatible functional API
# ----------------------------------------------------------------------

def load_coarse_map() -> dict:
    return _get_default_domain_mapper().load_coarse_map()


def map_fine_to_coarse(fine_label: str) -> str:
    return _get_default_domain_mapper().map_fine_to_coarse(fine_label)


def guess_fine_label_from_name(project: str) -> Optional[str]:
    return _get_default_domain_mapper().guess_fine_label_from_name(project)


def infer_domain(profile: ProjectProfile) -> tuple[str, Optional[str]]:
    return _get_default_domain_mapper().infer_domain(profile)


def clone_repo_if_needed(main_repo: str, target_dir: Path) -> None:
    augmenter = ProfileAugmenter(clone_root=target_dir.parent, domain_mapper=_get_default_domain_mapper())
    augmenter.clone_repo_if_needed(main_repo, target_dir)


def compute_loc(repo_dir: Path) -> int:
    augmenter = ProfileAugmenter(clone_root=repo_dir, domain_mapper=_get_default_domain_mapper())
    return augmenter.compute_loc(repo_dir)


def augment_profile(
    profile: ProjectProfile,
    clone_root: Path,
) -> ProjectProfile:
    augmenter = ProfileAugmenter(clone_root=clone_root, domain_mapper=_get_default_domain_mapper())
    return augmenter.augment(profile)


class ProfileAugmentWorker:
    """
    Worker object executed in a subprocess.
    It processes a slice of profile paths and augments each profile.
    """

    def __init__(self, paths: List[Path], clone_root: Path) -> None:
        self.paths = paths
        self.clone_root = clone_root

    def StartRun(self) -> None:
        from .profiles import load_profile, save_profile  # import inside process
        augmenter = ProfileAugmenter(clone_root=self.clone_root)

        total = len(self.paths)
        for idx, path in enumerate(self.paths, start=1):
            profile = load_profile(path)
            #if not "tensorflow" in profile.project.lower():
            #    continue
            print(f"[worker] {path.name} ({idx}/{total})")
            profile = augmenter.augment(profile)
            save_profile(profile, path)


class AugmentTaskDistributer(TaskDistributer):
    """
    TaskDistributer specialization for profile augmentation.
    Splits the list of profile paths into ranges and spawns workers.
    """

    def __init__(
        self,
        task_name: str,
        paths: List[Path],
        clone_root: Path,
        task_num: int = 4,
    ) -> None:
        super().__init__(task_name, ItemSize=len(paths), TaskNum=task_num)
        self.paths = paths
        self.clone_root = clone_root

    def InitObject(self, StartNo: int, EndNo: int) -> ProfileAugmentWorker:
        # EndNo is inclusive in your TaskDistributer
        slice_paths = self.paths[StartNo : EndNo + 1]
        return ProfileAugmentWorker(slice_paths, self.clone_root)

    def Final(self) -> None:
        # Called once after all tasks join
        print("[augment] all worker processes finished.")

