-- conf/tls.lua
-- TLS/SSL-focused profile: binds SSL/TLS inspector (named "ssl") by service and common ports.
-- Run:
--   ./snort -c conf/tls.lua -r input.pcap

require('snort_defaults')

HOME_NET = 'any'
EXTERNAL_NET = 'any'

stream_tcp = { }
wizard = { }

-- SSL/TLS inspector (Snort docs refer to SSL/TLS service inspection)
ssl = { }

binder =
{
  { when = { proto = 'tcp' }, use = { type = 'stream_tcp' } },

  -- Common TLS ports (keep minimal; add more if you want)
  { when = { proto = 'tcp', ports = '443', role = 'server' }, use = { type = 'ssl' } },
  { when = { proto = 'tcp', ports = '8443', role = 'server' }, use = { type = 'ssl' } },

  -- Also bind if wizard tags service as 'ssl'
  { when = { service = 'ssl' }, use = { type = 'ssl' } },

  { use = { type = 'wizard' } },
}

ips = { }

