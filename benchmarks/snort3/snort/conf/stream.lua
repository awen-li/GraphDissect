-- conf/stream.lua
-- Stream-heavy profile: keep stream tracking/reassembly on, tweak a couple knobs.
-- Run:
--   ./snort -c conf/stream.lua -r input.pcap

require('snort_defaults')

HOME_NET = 'any'
EXTERNAL_NET = 'any'

-- Slightly more explicit stream tuning (keep conservative; avoid huge memory spikes)
stream_tcp =
{
  -- If you want stress: raise max_pdu; if you want safety: keep default.
  -- max_pdu = 32768,
  reassemble_async = true,
  -- session_timeout = 180,
}

stream_udp  = { }
stream_icmp = { }
wizard      = { }

binder =
{
  { when = { proto = 'tcp'  }, use = { type = 'stream_tcp'  } },
  { when = { proto = 'udp'  }, use = { type = 'stream_udp'  } },
  { when = { proto = 'icmp' }, use = { type = 'stream_icmp' } },
  { use = { type = 'wizard' } },
}

ips = { }

