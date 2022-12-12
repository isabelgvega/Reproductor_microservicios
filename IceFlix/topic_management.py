#!/usr/bin/env python3
import IceStorm


def obtainTopic(tp_manager, tp):

    try:

        tp = tp_manager.retrieve(tp)

    except IceStorm.NoSuchTopic:

        tp = tp_manager.create(tp)
        print("Topic Not Found. New Topic created.")

    finally:

        return tp

proxy_topicManager = 'IceStorm/TopicManager:tcp -p 10000' 

def obtainManager(msgBroker):

    global proxy_topicManager

    topicProxy = msgBroker.stringToProxy(proxy_topicManager)
    topicManager = IceStorm.TopicManagerPrx.checkedCast(topicProxy)

    if not topicManager: 

        raise ValueError(f'The proxy {topicProxy} is incorrect') 

    return topicManager
