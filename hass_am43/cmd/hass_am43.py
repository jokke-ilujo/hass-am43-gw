import sys

from mqtt.client.factory import MQTTFactory
from oslo_config import cfg
from twisted.internet import reactor
from twisted.internet.endpoints import clientFromString

from hass_am43 import config
from hass_am43 import logging
from hass_am43.services.mqtt_service import MQTTService


CONF = cfg.CONF
log = logging.log


def fail(e):
    sys.stderr.write("ERROR: %s\n" % str(e))
    sys.exit(99)


def main():
    try:
        config.parse_args()
        config.register_blinds(CONF)
    except Exception as e:
        fail(e)
    logging.startLogging()
    logging.setLogLevel(namespace='mqtt', levelStr='debug')
    logging.setLogLevel(levelStr='debug')

    factory = MQTTFactory(profile=MQTTFactory.SUBSCRIBER |
                          MQTTFactory.PUBLISHER)
    broker = ("tcp:" + CONF.mqtt.broker_address + ":" +
              str(CONF.mqtt.broker_port))
    credentials = {}
    if CONF.mqtt.username:
        credentials["username"] = CONF.mqtt.username
    if CONF.mqtt.username and CONF.mqtt.password:
        credentials["password"] = CONF.mqtt.password
    myEndpoint = clientFromString(reactor, broker)
    serv = MQTTService(myEndpoint, factory, broker, credentials)
    serv.startService()
    reactor.run()


if __name__ == '__main__':
    main()
