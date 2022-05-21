import am43
import json
from oslo_config import cfg
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet import reactor, task
from twisted.internet.defer import inlineCallbacks, DeferredList

from hass_am43 import logging


CONF = cfg.CONF
log = logging.log


class MQTTService(ClientService):

    def __init__(self, endpoint, factory, broker, credentials):
        ClientService.__init__(self, endpoint, factory,
                               retryPolicy=backoffPolicy())
        self.broker = broker
        if credentials:
            self.credentials = credentials
        else:
            self.credentials = {}
        self.blinds = {}
        for am43_b in CONF.am43_blinds:
            self.blinds[am43_b] = {'mac': getattr(CONF, am43_b).mac_address,
                                   'location': getattr(CONF, am43_b).location}
        self.blinds_config = []
        for bid, blind in self.blinds.items():
            b_conf = {'name': "AM43 Blind",
                      'device_class': "cover",
                      'object_id': bid,
                      'platform': "mqtt",
                      'qos': 2,
                      '~': "homeassistant/cover/{}".format(bid),
                      'set_pos_t': "~/set_position",
                      'pos_t': "~/position",
                      'position_open': 0,
                      'position_closed': 100}
            self.blinds_config.append(b_conf)

    def _logFailure(failure):
        log.debug("reported {message}", message=failure.getErrorMessage())
        return failure

    def _log_all_pub(*args):
        log.debug("all publishing complete args={args!r}", args=args)

    def startService(self):
        log.info("starting MQTT Client Service")
        # whenConnected() inherited from ClientService
        self.whenConnected().addCallback(self.connect_to_broker)
        ClientService.startService(self)

    @inlineCallbacks
    def connect_to_broker(self, protocol,
                          interval: float = 1200.0):
        '''
        Connect to MQTT broker
        '''
        self.protocol = protocol
        self.protocol.onPublish = self.on_publish
        self.protocol.onDisconnection = self.on_disconnection
        self.protocol.setWindowSize(3)
        self.task = task.LoopingCall(self.publish_positions,
                                     CONF.am43_blinds)
        self.task.start(interval)
        try:
            yield self.protocol.connect("TwistedMQTT-hass-am43",
                                        keepalive=60,
                                        **self.credentials)
            yield self.subscribe()
        except Exception as e:
            log.error("Connecting to {broker} raised {excp!s}",
                      broker=self.broker, excp=e)
        else:
            log.info("Connected and subscribed to {broker}",
                     broker=self.broker)
        try:
            yield self.publish_config()
            yield self.publish_positions(self.blinds.keys())
        except Exception as e:
            log.error("Publishing to {broker} raised {excp!s}",
                      broker=self.broker, excp=e)
        else:
            log.info("Published cover configs.")

    def subscribe(self):

        def _logGrantedQoS(value):
            log.debug("response {value!r}", value=value)
            return True

        def _logAll(*args):
            log.debug("all subscriptions complete args={args!r}", args=args)

        d = []
        for b_conf in self.blinds_config:
            sub = self.protocol.subscribe(b_conf['~'] +
                                          b_conf['set_pos_t'][1:], 2)
            sub.addCallbacks(_logGrantedQoS, self._logFailure)
            d.append(sub)

        dlist = DeferredList(d, consumeErrors=True)
        dlist.addCallback(_logAll)
        return dlist

    def publish_config(self):

        log.debug(" >< Sending config messages >< ")
        cl = []
        for b_conf in self.blinds_config:
            conf_pub = self.protocol.publish(
                topic=b_conf['~'] + '/config',
                qos=b_conf['qos'],
                message=json.dumps(b_conf)
            )
            conf_pub.addErrback(self._log_failure)
        dlist = DeferredList(cl, consumeErrors=True)
        dlist.addCallback(self._log_all_pub)
        return dlist

    def publish_positions(self, keys=[]):

        log.debug(" >< Collecting blinds states >< ")
        blinds_states = {}
        for key in keys:
            blind_engine = am43.search(self.blinds[key]['mac'])
            blinds_states[key] = blind_engine.get_properties()
        else:
            return
        log.debug(" >< Publishing positions >< ")
        states_list = []
        for key, states in blinds_states.items():
            b_conf = next(item for item in self.blinds_config if
                          item['object_id'] == key)
            topic = b_conf['~'] + b_conf['pos_t'][1:]
            states_list.append(
                self.protocol.publish(topic=topic,
                                      qos=b_conf['qos'],
                                      message=states['position'])
            )
            states_list[-1].addErrback(self._log_failure)
        dlist = DeferredList(states_list, consumeErrors=True)
        dlist.addCallback(self._log_all_pub)
        return dlist

    def on_publish(self, topic, payload, qos, dup, retain, msgId):
        '''
        Callback Receiving messages from publisher
        '''
        log.debug("topic={topic} msg={payload}".format(topic=topic,
                                                       payload=payload))
        blind = next((item for item in self.blinds_config if
                      item['~'] + item['set_pos_t'][1:] == topic), False)
        if blind:
            blind_engine = am43.search(self.blinds[blind['object_id']]['mac'])
            blind_engine.set_postion(pecentage=payload)
            d = task.deferLater(reactor,
                                30,
                                self.publish_positions,
                                [blind['object_id']])
            d.addErrback(self._log_failure)
            d.addCallback(self._log_all_pub)
            return d

    def on_disconnection(self, reason):
        '''
        get notfied of disconnections
        and get a deferred for a new protocol object (next retry)
        '''
        log.debug(" >< Connection was lost ! ><, reason={r}", r=reason)
        self.whenConnected().addCallback(self.connectToBroker)
