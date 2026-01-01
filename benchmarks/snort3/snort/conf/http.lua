-- conf/http.lua
-- HTTP-focused profile (still works for generic pcaps).
-- Run:
--   ./snort -c conf/http.lua -r input.pcap

require('snort_defaults')

HOME_NET = 'any'
EXTERNAL_NET = 'any'

stream_tcp = { }
stream_udp = { }
stream_icmp = { }
wizard = { }

-- HTTP inspector (defaults)
http_inspect = { }

binder =
{
  { when = { proto = 'tcp' }, use = { type = 'stream_tcp' } },
  { when = { proto = 'udp' }, use = { type = 'stream_udp' } },

  -- If the wizard tags a flow as HTTP, bind http_inspect
  { when = { service = 'http' }, use = { type = 'http_inspect' } },

  { use = { type = 'wizard' } },
}

ips = { }

