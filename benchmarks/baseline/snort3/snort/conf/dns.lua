-- conf/dns.lua
-- DNS-focused profile: binds DNS inspector by port 53 + service tagging.
-- Run:
--   ./snort -c conf/dns.lua -r input.pcap

require('snort_defaults')

HOME_NET = 'any'
EXTERNAL_NET = 'any'

stream_tcp = { }
stream_udp = { }
wizard = { }

-- DNS inspector (defaults)
dns = { }

binder =
{
  { when = { proto = 'tcp' }, use = { type = 'stream_tcp' } },
  { when = { proto = 'udp' }, use = { type = 'stream_udp' } },

  -- Bind DNS by well-known server port
  { when = { proto = 'udp', ports = '53', role = 'server' }, use = { type = 'dns' } },
  { when = { proto = 'tcp', ports = '53', role = 'server' }, use = { type = 'dns' } },

  -- Also bind if wizard labels service as DNS
  { when = { service = 'dns' }, use = { type = 'dns' } },

  { use = { type = 'wizard' } },
}

ips = { }

