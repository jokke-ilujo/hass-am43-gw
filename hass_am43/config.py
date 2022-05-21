import copy

from oslo_config import cfg

from hass_am43 import version

blind_engines_opts = [
        cfg.ListOpt('am43_blinds',
                    sample_default=['window1', 'window2'],
                    help="List of IDs of the blind engines"
                    ),
        cfg.FloatOpt('polling_interval',
                     default=1200.0,
                     min=30.0,
                     help=("The interval of the status poll of the blind when",
                           " not moving, in seconds. This will affect battery",
                           " life.")
                     )
        ]
mqtt_broker_opts = [
        cfg.HostAddressOpt('broker_address',
                           help="Valid IP or hostname of the broker."
                           ),
        cfg.PortOpt('broker_port',
                    default=1883,
                    help="Valid port number the broker is listening."),
        cfg.StrOpt('username',
                   default="am43-gw",
                   help="The user name to authenticate with the broker."),
        cfg.StrOpt('password',
                   default=None,
                   help="The users password for mqtt broker.")
        ]
blind_opts = [
        cfg.StrOpt('mac_address',
                   sample_default="XX:XX:XX:XX:XX:XX",
                   help="Bluetooth MAC address for the blind."),
        cfg.StrOpt('location',
                   sample_default="Living Room",
                   help="Physical location of said blind.")
]


_all_opts = [
        ('', blind_engines_opts),
        ('mqtt', mqtt_broker_opts),
        ('window1', blind_opts),
        ('window2', blind_opts),
        ]

CONF = cfg.CONF
CONF.register_opts(blind_engines_opts)
CONF.register_opts(mqtt_broker_opts, group='mqtt')


def parse_args(args=None, usage=None, default_config_files=None):
    CONF(args=args,
         project='hass-am43',
         version=version.version(),
         usage=usage,
         default_config_files=default_config_files)


def list_opts():
    return [(group, copy.deepcopy(opt)) for group, opt in _all_opts]


def register_blinds(conf):
    configured_blinds = copy.deepcopy(conf.am43_blinds)
    for blind in configured_blinds:
        conf.register_opts(blind_opts, group=blind)
