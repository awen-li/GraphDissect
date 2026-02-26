-- conf/min.lua
-- Minimal offline config for reading pcaps with basic flow tracking + service ID.
-- Run example:
--   ./snort -c conf/min.lua -r input.pcap

-- If your snort binary can't find snort_defaults.lua automatically, add:
--   ./snort -L /path/to/lua -c conf/min.lua -r input.pcap
require('snort_defaults')

HOME_NET = 'any'
EXTERNAL_NET = 'any'

-- Core inspectors (defaults are fine)
stream_tcp = { }
stream_udp = { }
stream_icmp = { }
wizard     = { }

-- Binder: pick inspectors per flow (and let wizard auto-identify when possible)
binder =
{
  { when = { proto = 'tcp'  }, use = { type = 'stream_tcp'  } },
  { when = { proto = 'udp'  }, use = { type = 'stream_udp'  } },
  { when = { proto = 'icmp' }, use = { type = 'stream_icmp' } },

  -- Auto-select service inspectors based on wizard heuristics.
  { use = { type = 'wizard' } },
}

-- Keep IPS defaults (you can pass -R at runtime if desired)
ips = { }

