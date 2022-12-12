#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import threading
import topic_management
import IceStorm
import sys 
import random
import time
import uuid
import Ice
Ice.loadSlice('iceflix.ice')
import IceFlix

actualizado = False
available_princ = {}
available_au = {}
available_cat = {}
available_stream = {}

class ServicioAnuncios(IceFlix.ServiceAnnouncements):

    def __init__(self, principal, administrador, srvId):

        self.principal = principal
        self.adminToken = administrador
        self.srvId = srvId
    
    def newService(self, service, srvId, current=None):

        global available_princ
        global available_au
        global available_cat
        global available_stream
        
        if srvId == self.srvId:

            logging.debug("Received own announcement. Ignoring")
            return
        
        else:

            proxy = IceFlix.MainPrx.checkedCast(service)
            if not proxy:

                logging.debug("New service isn't of my type. Ignoring") 
            
            elif srvId not in available_princ:

                    available_princ[srvId] = IceFlix.MainPrx.uncheckedCast(service)

                    if not len(available_princ) <= 0:

                        mainCreado = IceFlix.MainPrx.uncheckedCast(service)
                        authenticators = self.principal.listAuth()
                        mediaCatalogs = self.principal.listCatalogs()
                        srv_volatil = VolatileServices(authenticators, mediaCatalogs)
                        mainCreado.updateDB(srv_volatil, self.srvId)
                        print("[MAIN]: A new service has been created ::IceFlix::Main")

            proxy = IceFlix.AuthenticatorPrx.checkedCast(service)

            if not proxy:
                logging.debug("New service isn't of my type. Ignoring")

            elif srvId not in available_au:

                    available_au[srvId] = IceFlix.AuthenticatorPrx.uncheckedCast(service)
                    print("[MAIN]: A new service has been created ::IceFlix::Authenticator")

            proxy = IceFlix.MediaCatalogPrx.checkedCast(service)
            if not proxy:
                logging.debug("New service isn't of my type. Ignoring")

            elif srvId not in available_cat:

                    available_cat[srvId] = IceFlix.MediaCatalogPrx.uncheckedCast(service)
                    print("[MAIN]: A new service has been created ::IceFlix::MediaCatalog", flush=True)
            
            proxy = IceFlix.StreamProviderPrx.checkedCast(service)
            if not proxy:
                logging.debug("New service isn't of my type. Ignoring")
                return

            elif srvId not in available_stream:

                    available_stream[srvId] = IceFlix.StreamProviderPrx.uncheckedCast(service)
                    print("[MAIN]: A new service has been created ::IceFlix::StreamProvider", flush=True)


    def removeSrv(self, srvId, tipoServicio):

        global available_cat
        global available_au
        
        print("[MAIN]: Removing service {}".format(srvId))

        if tipoServicio == '::IceFlix::Authenticator':

            del available_au[srvId]
        
        elif tipoServicio == '::IceFlix::MediaCatalog':

            del available_cat[srvId]

    def announce(self, service, srvId, current=None):

        global available_princ
        global available_au
        global available_cat
        global available_stream

        if srvId == self.srvId:
            
            logging.debug("Received own announcement or already known. Ignoring")
            return

        else:

            if service.ice_isA('::IceFlix::Main') and srvId not in available_princ:

                available_princ[srvId] = IceFlix.MainPrx.uncheckedCast(service)
                print("[MAIN]: Received service announcement ::IceFlix::Main", flush=True)

            if service.ice_isA('::IceFlix::Authenticator') and srvId not in available_au:

                available_au[srvId] = IceFlix.AuthenticatorPrx.uncheckedCast(service)
                print("[MAIN]: Received service announcement ::IceFlix::Authenticator")

            if service.ice_isA('::IceFlix::MediaCatalog') and srvId not in available_cat:

                available_cat[srvId] = IceFlix.MediaCatalogPrx.uncheckedCast(service)
                print("[MAIN]: Received service announcement ::IceFlix::MediaCatalog")

            if service.ice_isA('::IceFlix::StreamProvider') and srvId not in available_stream:

                available_stream[srvId] = IceFlix.StreamProviderPrx.uncheckedCast(service)
                print("[MAIN]: Received service announcement ::IceFlix:StreamProvider")           
    


class VolatileServices(IceFlix.VolatileServices):
    
    def __init__(self, authenticators, mediaCatalogs):
        
        self.authenticators = authenticators
        self.mediaCatalogs = mediaCatalogs   
                    

class Principal(IceFlix.Main):

    def __init__(self, administradorToken):
        
        self.adminToken = administradorToken
    
    def getCatalog(self, current = None):

        retornoCat = None
        incorrect = True
        global available_cat

        try:

            catalogo = random.choice(list(available_cat.values()))
            catalogo.ice_ping()
            retornoCat = catalogo
            incorrect = False
            
        except Exception as ex:
            print("[MAIN]: Error, something went wrong while getting Catalog")

        if incorrect == False:

            return IceFlix.MediaCatalogPrx.checkedCast(retornoCat) 

        else:

            raise IceFlix.TemporaryUnavailable()

    def getAuthenticator(self, current = None):
        
        retornoAu = None
        incorrect = True
        global available_au
        
        try:
            auth = random.choice(list(available_au.values()))
            auth.ice_ping()
            retornoAu = auth
            incorrect = False

        except Exception as ex:
            pass

        if incorrect == False:

            return IceFlix.AuthenticatorPrx.checkedCast(retornoAu) 

        else:
            
            raise IceFlix.TemporaryUnavailable()
                

    def updateDB(self, currentServices, srvId, current=None):

        global actualizado

        global available_princ
        global available_au
        global available_cat
        

        if actualizado == False:

            print("[MAIN]: Data is being updated")

            if srvId not in available_princ.keys():
                
                print("[MAIN]: An error occurred")
                raise IceFlix.UnknownService
        
            for au in currentServices.authenticators:

                id = str(id.uuid4())
                available_au[id] = au
            
            for cat in currentServices.mediaCatalogs: 

                id = str(id.uuid4())
                available_cat[id] = cat
            
            actualizado = True
            print("[MAIN]: Data has already been updated")

    def isAdmin(self, adminToken, current = None):

        validAuth = False
        print("[MAIN]: El admintoken que le llega:{}".format(adminToken))
        print("[MAIN]: El admintoken que es:{}".format(self.adminToken))
        if adminToken.__eq__(self.adminToken):
            validAuth = True
            return validAuth
            
        return validAuth
    
           
        
    def listCatalogs(self):

        listCat = []
        global available_cat
        
        for cat in available_cat:
            listCat.append(cat)
        
        return listCat
    
    def listAuth(self): 

        listAuthent = []
        global available_au
        
        for au in available_au:
            listAuthent.append(au)
            
        return listAuthent

class App(Ice.Application):

    def threadsInitialization(self, topic_announce, servicio, srvId):

        publicador = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(topic_announce.getPublisher())
        publicador.newService(servicio, srvId)
    
        time.sleep(4) 
        
        while True:

            try:

                publicador = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(topic_announce.getPublisher())
                publicador.announce(servicio, srvId)
 
                time.sleep(11)  

            except Ice.CommunicatorDestroyedException as exception:
                
                print("[MAIN]: -> CommunicatorDestroyedException")
                break
    
    def run(self, argv):
        
        global available_au
        global available_cat
        global available_princ
        no_error = True

        logging.debug('Running...')

        srvId = str(uuid.uuid4())
        proper=Ice.createProperties()
        proper.load("./configs/principal.conf")
        tkn=proper.getProperty("principal.admin_token")
        adaptador = self.communicator().createObjectAdapterWithEndpoints('MainAdapter', 'tcp') 
        adaptador.activate()
        adminTopics = topic_management.obtainManager(self.communicator())

        sirviente = Principal(tkn)
        proxy = adaptador.addWithUUID(sirviente)
        print('{}'.format(proxy), flush=True) 
        announceService = ServicioAnuncios(sirviente, tkn, srvId)

        topic_announce = topic_management.obtainTopic(adminTopics, 'ServiceAnnouncements') 

        proxy_announce = adaptador.addWithUUID(announceService)
        topic_announce.subscribeAndGetPublisher({}, proxy_announce)
        time.sleep(12)


        if not len(available_princ) <= 0:

            principal = random.choice(list(available_princ.values()))
            no_error = principal.isAdmin(tkn)
        
        if no_error:

            try:
                threading.Thread(
                    target=self.threadsInitialization,
                    args=(
                        topic_announce,
                        proxy,
                        srvId,
                    ),
                ).start()
            except Exception as ex:
                print(ex)
            
            print('--Running Main Server--')
            while True:            
                try:

                    for cat in available_cat:
                        try:
                            available_cat[cat].ice_ping()
                            
                        except Ice.ConnectFailedException:   
                            announceService.removeSrv(cat, '::IceFlix::MediaCatalog')
                            break

                    for au in available_au:
                        try:
                            available_au[au].ice_ping()

                        except Ice.ConnectFailedException:
                            announceService.removeSrv(au, '::IceFlix::Authenticator')
                            break

                    
                    time.sleep(11)  
                except KeyboardInterrupt:                                
                    break

        else:
            print("[MAIN]: -> Error: Admin Token Failure")
            sys.exit(1)

            
        self.shutdownOnInterrupt()      
        self.communicator().waitForShutdown()

        topic_announce.unsubscribe(proxy_announce)
        
        return 0
    
    def obtainProxy_announce(self, adminTopics):

        topic_announce = topic_management.obtainTopic(adminTopics, 'ServiceAnnouncements')
        announcePubli = topic_announce.getPublisher()
        proxy_announce = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(announcePubli)

        return proxy_announce
    
    

if __name__ == '__main__':

    PRINCIPAL = App()
    sys.exit(PRINCIPAL.main(sys.argv)) 