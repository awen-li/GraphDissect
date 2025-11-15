import json
import subprocess
from pathlib import Path
from typing import Optional

from .profiles import ProjectProfile

# You can extend or refine these domain labels as you go
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
}


def clone_repo_if_needed(main_repo: str, target_dir: Path) -> None:
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


def _compute_loc_with_cloc(repo_dir: Path) -> Optional[int]:
    try:
        proc = subprocess.run(
            ["cloc", "--json", "."],
            cwd=str(repo_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        data = json.loads(proc.stdout)
        total = 0
        for lang, info in data.items():
            if not isinstance(info, dict):
                continue
            code = info.get("code")
            if isinstance(code, int):
                total += code
        return total
    except Exception as e:
        print(f"[loc] cloc failed in {repo_dir}: {e}")
        return None


def _compute_loc_fallback(repo_dir: Path) -> int:
    exts = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".hxx"}
    total = 0
    for p in repo_dir.rglob("*"):
        if p.is_file() and p.suffix in exts:
            try:
                with p.open("r", errors="ignore") as f:
                    for _ in f:
                        total += 1
            except Exception:
                continue
    return total


def compute_loc(repo_dir: Path) -> int:
    loc = _compute_loc_with_cloc(repo_dir)
    if loc is not None:
        return loc
    return _compute_loc_fallback(repo_dir)


def infer_domain(profile: ProjectProfile) -> str:
    # If already set (non-empty), keep it
    if profile.domain and profile.domain.lower() not in ("unknown", "null"):
        return profile.domain

    # Try overrides by project name
    if profile.project in KNOWN_DOMAIN_OVERRIDES:
        return KNOWN_DOMAIN_OVERRIDES[profile.project]

    # Fall back on language if useful later (e.g., "c" -> "systems")
    # For now, just "unknown"
    return "unknown"


def augment_profile(
    profile: ProjectProfile,
    clone_root: Path,
) -> ProjectProfile:
    """
    Clone the upstream repo, compute LOC, and update domain.
    """
    if not profile.main_repo or profile.main_repo.lower().startswith("null"):
        print(f"[augment] Skipping {profile.project}: no main_repo")
        return profile

    repo_dir = clone_root / profile.project
    clone_repo_if_needed(profile.main_repo, repo_dir)

    if not repo_dir.is_dir():
        print(f"[augment] Skipping {profile.project}: repo directory not found")
        return profile

    loc_val = compute_loc(repo_dir)
    domain_val = infer_domain(profile)

    profile.loc = loc_val
    profile.domain = domain_val

    print(f"[augment] {profile.project}: loc={loc_val}, domain={domain_val}")
    return profile

