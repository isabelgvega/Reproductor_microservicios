#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import getpass
import time

from httplib2 import Authentication
import rtsputils
import hashlib
import re
from os import listdir
from os.path import isfile
import sys
import threading
import topic_management
import Ice
Ice.loadSlice('iceflix.ice')
import IceFlix
PORT_CLI = 9092
INTENTOS_MAX = 4
tituloBuscado = ''
tknUsuario = ''
intento = 0
resultadoBusqueda = ''
ADMIN_TOKEN = ''


class Client(Ice.Application):

    def __init__(self):

        self.connected = False
        self.nameUser = ""
        self.pswd = ""
        self.proxyPrincipal = None
        self.proxyRevocs= None
        self.pswHash = ""
        self.intento = 0
        tknUsuario = ""

    def idCalculation(self, mediaFile):

        idHash = hashlib.sha256()

        with open(mediaFile, "rb") as arch:

            for bloqueBytes in iter(lambda: arch.read(4096), b""):

                idHash.update(bloqueBytes)

        return idHash.hexdigest()

    def idFiles_initialization(self, mediaFiles):

        idMediaFiles = []

        for arch in mediaFiles:

            idMediaFiles.append(self.idCalculation(arch))

        return idMediaFiles

    def files_initialization(self, dirRaiz):

        mediaFiles = []

        for arch in listdir(dirRaiz):

            if isfile(dirRaiz+arch):

                mediaFiles.append(dirRaiz+arch)

        return mediaFiles

    def login(self, proxyPrincipal):

        numIntentos = 0
        global tknUsuario
        global ADMIN_TOKEN
        validUser = False

        while not numIntentos >= INTENTOS_MAX:

            try:

                proxyAuth = proxyPrincipal.getAuthenticator()

                self.nameUser = input(f"Enter Username: ")
                self.pswd = getpass.getpass(f"Enter Password: ")
                self.pswHash = hashlib.sha256(self.pswd.encode()).hexdigest()

                tknUsuario = proxyAuth.refreshAuthorization(
                    self.nameUser, self.pswHash)
                validUser = True
                return validUser, self.nameUser, self.pswHash

            except IceFlix.Unauthorized:

                print(f"Error, invalid user\n")
                self.nameUser = ""
                validUser = False

                return validUser, None, None

            except IceFlix.TemporaryUnavailable:

                if numIntentos >= INTENTOS_MAX:

                    print(
                        f"-> Service Error. WARNING: All connection attempts have been spent\n")
                    validUser = False

                    return validUser, None, None

                else:

                    print(f"-> Service Error, restarting connection.\n")

                numIntentos = numIntentos + 1
                time.sleep(12)
                pass

            except Exception as error:

                self.nameUser = ""
                print("Exception, the login has not been successful")
                validUser = False

                return validUser, None, None

    def connect(self):

        inPrx = input(f"Please, enter the main Proxy: ")
        prx = self.communicator().stringToProxy(inPrx)

        proxyPrincipal = IceFlix.MainPrx.checkedCast(prx)
        numIntentos = 0

        if not proxyPrincipal:

            prx = self.communicator().stringToProxy(inPrx)
            proxyPrincipal = IceFlix.MainPrx.checkedCast(prx)

            if numIntentos >= INTENTOS_MAX:

                print(
                    f"-> Service Error. WARNING: All connection attempts have been spent\n")

                return None

            else:

                print(f"-> Service Error, restarting connection.\n")

            numIntentos = numIntentos + 1
            time.sleep(12)

        else:

            return proxyPrincipal

    def connectStream(self):

        inPrxStream = input(f"Please, enter the streaming Proxy: ")
        prxStream = self.communicator().stringToProxy(inPrxStream)

        streamProv_Proxy = IceFlix.StreamProviderPrx.checkedCast(prxStream)
        numIntentos = 0

        if not streamProv_Proxy:

            prxStream = self.communicator().stringToProxy(inPrxStream)

            streamProv_Proxy = IceFlix.MainPrx.checkedCast(prxStream)

            if numIntentos >= INTENTOS_MAX:

                print(
                    f"-> Service Error. WARNING: All connection attempts have been spent\n")

                return None

            else:

                print(f"-> Service Error, restarting connection.\n")

            numIntentos = numIntentos + 1
            time.sleep(12)

        else:
            return streamProv_Proxy

    def mediaStreaming(self, msgBroker, proxyPrincipal, tknUsuario):

        nameDirectorio = "resources/"
        numIntentos = 0
        validStream = True

        try:

            self.catalogSearch(proxyPrincipal)
            contador = 0
            inName = ""

            identifier = input(
                f"-> Please, enter the identifier of the file you want to play: ")

            mediaFiles = self.files_initialization(nameDirectorio)
            idMediaFiles = self.idFiles_initialization(mediaFiles)

            for arch in mediaFiles:

                idArchivo = idMediaFiles[contador]

                if identifier.__eq__(idArchivo):
                    inName = mediaFiles[contador]
                    print(inName)
                    break

                contador += 1

            if inName.__eq__(""):

                contador = 0
                nameDirectorio = "resources_to_upload/"

                mediaFiles = self.files_initialization(nameDirectorio)
                idMediaFiles = self.idFiles_initialization(mediaFiles)

                for arch in mediaFiles:

                    idArchivo = idMediaFiles[contador]

                    if identifier.__eq__(idArchivo):
                        inName = mediaFiles[contador]
                        print(inName)
                        break

                    contador += 1

            proxyAuthentication = proxyPrincipal.getAuthenticator()

            catalogPrx = proxyPrincipal.getCatalog()
            catalogMedia = catalogPrx.getTile(identifier, tknUsuario)
            prxStream = catalogMedia.provider

            controlStream = prxStream.getStream(identifier, tknUsuario)
            streamRTP = controlStream.getSDP(tknUsuario, PORT_CLI)

            adminTopic = topic_management.obtainManager(msgBroker)
            topicStream = topic_management.obtainTopic(
                adminTopic, controlStream.getSyncTopic())

            synStream = StreamSync(
                topicStream, controlStream, proxyAuthentication, self.nameUser, self.pswHash)
            proxyStream = self.adapter.addWithUUID(synStream)

            topicStream.subscribeAndGetPublisher({}, proxyStream)

            reproductor = rtsputils.RTSPPlayer()

            print(f"\r--- Video {inName} is playing ---\n")
            reproductor.play(streamRTP)

            time.sleep(10)

            reproductor.stop()
            controlStream.stop()

        except IceFlix.TemporaryUnavailable:

            if numIntentos >= INTENTOS_MAX:
                print(
                    f"-> Service Error. WARNING: All connection attempts have been spent\n")

                validStream = False
                return validStream

            else:

                print(f"-> Service Error, restarting connection.\n")

            numIntentos = numIntentos + 1
            pass

        except IceFlix.Unauthorized:

            print(f"-> Error, you do not have correct authorization\n")

            validStream = False
            return validStream

        except IceFlix.WrongMediaId:

            print(f"-> Error, file not found\n")

            validStream = False
            return validStream

        except Exception as error:

            print(error)
            print("Exception, the playback has not been successful")

            validStream = False
            return validStream
    def printResultados(self,lista):
        print(f"Answers found:\n")
        resultado=''.join(map(str,lista))
        splitted=resultado.split(", ")
        id=splitted[0][2:-1]
        nombre=splitted[1][1:-2]
        print("[CLIENTE]: Result - ID: {}, Nombre: {}".format(id,nombre))
    def catalogSearch(self, proxyPrincipal):

        numIntentos = 0
        validSearch = True
        finMenu = False
        global tknUsuario
        global resultadoBusqueda

        while not numIntentos >= INTENTOS_MAX:

            try:

                catalogPrx = proxyPrincipal.getCatalog()

                print(f"-> Please, select search criteria: \n")

                print(f"\r 1 - By tags\n")
                print(f"\r 2 - By name\n")

                option = int(
                    input(f"-> Enter the number corresponding to the desired option: "))

                if option == 1:

                    print(f"-> Please, select the desired search criteria:\n")

                    print(f"\r 1 - Names with all of the tags\n")
                    print(f"\r 2 - Names with any of the tags\n")

                    subOption = int(
                        input(f"-> Enter the number corresponding to the desired option: "))

                    if subOption == 1:

                        allTagsMatch = True

                    elif subOption == 2:

                        allTagsMatch = False

                    else:

                        print(f"-> Error, you have selected an invalid option\n")
                        break

                    searchTags = input(
                        f"-> Please, write the tags, separated by semicolons (;), that you want to search for: ")
                    searchTags = re.sub("\s+", "", searchTags.strip())

                    listadoTags = searchTags.split(';')
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    listadoResults = catalogPrx.getTilesByTags(
                        listadoTags, allTagsMatch, tknUsuario)

                    if str(listadoResults).__eq__("[]"):

                        print(f"-> No matches found\n")

                    else:
                        self.printResultados(listadoResults)


                elif option == 2:

                    print(f"-> Please, select the desired search criteria:\n")

                    print(f"\r 1 - Search terms are included in the name\n")
                    print(f"\r 2 - Exact name match\n")

                    subOption = int(
                        input(f"-> Enter the number corresponding to the desired option: "))

                    if subOption == 1:

                        accurateMatch = False

                    elif subOption == 2:

                        accurateMatch = True

                    else:

                        print(f"-> Error, you have selected an invalid option\n")
                        break

                    searchName = input(
                        f"-> Please, enter the name of the movie you want to search for: ")
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    listadoResults = catalogPrx.getTilesByName(
                        searchName, accurateMatch)

                    if str(listadoResults).__eq__("[]"):

                        print(f"-> No matches found\n")

                    else:

                         self.printResultados(listadoResults)
                else:

                    print(f"-> Error, you have selected an invalid option\n")
                    break

                finMenu = True
                return finMenu

            except IceFlix.TemporaryUnavailable:

                if numIntentos >= INTENTOS_MAX:
                    print(
                        f"-> Service Error. WARNING: All connection attempts have been spent\n")

                    validSearch = False
                    return validSearch

                else:

                    print(f"-> Service Error, restarting connection.\n")

                numIntentos = numIntentos + 1

                pass

            except IceFlix.Unauthorized:

                print(f"-> Error, you do not have correct authorization\n")

                validSearch = False
                return validSearch

            except Exception as error:

                print(error)

                validSearch = False
                return validSearch

    def catalogUpdate(self, proxyPrincipal):

        numIntentos = 0
        finMenu = False
        validUpdate = True
        global tknUsuario
        global tituloBuscado

        properties = Ice.createProperties()
        properties.load("./configs/cli.conf")
        ADMIN_TOKEN = properties.getProperty("cli.admin_token")

        while not numIntentos >= INTENTOS_MAX:

            try:

                catalogPrx = proxyPrincipal.getCatalog()
                print(f"-> Please, select the desired option: \n")

                print(f"\r 1 - Upload a film\n")
                print(f"\r 2 - Remove a film\n")
                print(f"\r 3 - Rename a film\n")
                print(f"\r 4 - Add tags to a film\n")
                print(f"\r 5 - Remove tags to a film\n")

                option = int(
                    input(f"-> Enter the number corresponding to the desired option: "))

                if option == 1:

                    idMediaFiles = []
                    mediaFiles = []
                    contador = 0

                    nameDirectorio = 'resources_to_upload/'

                    print(f"\r-> List of files that are allowed to upload: \n")
                    mediaFiles = self.files_initialization(nameDirectorio)
                    idMediaFiles = self.idFiles_initialization(mediaFiles)

                    for arch in mediaFiles:

                        idArchivo = idMediaFiles[contador]
                        nombreArchivo = mediaFiles[contador]

                        print(f"\r -> ID OF THE FILE: {idArchivo}\n")
                        print(f"\r -> NAME OF THE FILE: {nombreArchivo}\n")
                        contador += 1

                    inName = input(
                        f"-> Please, enter the name of the file you wish to upload to the system: ")

                    self.shutdownOnInterrupt()

                    mediaUp = MediaUploader(nameDirectorio + inName)
                    upPrx = self.adapter.addWithUUID(mediaUp)

                    upl = IceFlix.MediaUploaderPrx.checkedCast(upPrx)

                    mediaFiles = self.files_initialization('resources/')
                    idMediaFiles = self.idFiles_initialization(mediaFiles)

                    identifier = idMediaFiles[0]
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    catalogMedia = catalogPrx.getTile(identifier, tknUsuario)

                    prxStream = catalogMedia.provider
                    prxStream.uploadMedia(inName, upl, ADMIN_TOKEN)
                    print(
                        f"\r-> Operation completed successfully. File upload: {inName} \n")
                    contador = 0

                elif option == 2:

                    self.catalogSearch(proxyPrincipal)

                    identifier = input(
                        f"-> Please, enter the identifier of the file you want to remove: ")
                    #Necesario token admin
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    catalogMedia = catalogPrx.getTile(identifier, tknUsuario)

                    prxStream = catalogMedia.provider
                    prxStream.deleteMedia(identifier, ADMIN_TOKEN)
                    print(f"\r-> Operation completed successfully. File removed\n")

                elif option == 3:

                    self.catalogSearch(proxyPrincipal)

                    tituloBuscado = input(
                        f"-> Please, enter the identifier of the file you want to rename: ")
                    inName = input(
                        f"-> Please, type the new name that the file will have: ")
                    #Necesario token admin
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    catalogPrx.renameTile(tituloBuscado, inName, ADMIN_TOKEN)
                    print(f"\r-> Operation completed successfully. File renamed\n")

                elif option == 4:

                    self.catalogSearch(proxyPrincipal)

                    tituloBuscado = input(
                        f"-> Please, enter the identifier of the file you want to add new tags to: ")
                    tagsAdded = input(
                        f"-> Please, write the tags, separated by semicolons (;), that you want to add: ")

                    tagsAdded = re.sub("\s+", "", tagsAdded.strip())
                    tagsListado = tagsAdded.split(';')
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    catalogPrx.addTags(tituloBuscado, tagsListado, tknUsuario)
                    print(f"\r-> Operation completed successfully. Tags added\n")

                elif option == 5:

                    self.catalogSearch(proxyPrincipal)

                    tituloBuscado = input(
                        f"-> Please, enter the identifier of the file you want to remove tags from: ")
                    tagsRemoved = input(
                        f"-> Please, write the tags, separated by semicolons (;), that you want to remove: ")

                    tagsRemoved = re.sub("\s+", "", tagsRemoved.strip())
                    tagsListado = tagsRemoved.split(';')
                    catalogPrx = IceFlix.MediaCatalogPrx.checkedCast(
                        catalogPrx)
                    catalogPrx.removeTags(
                        tituloBuscado, tagsListado, tknUsuario)
                    print(f"\r-> Operation completed successfully. Tags removed\n")

                else:

                    print(f"-> Error, you have selected an invalid option\n")
                    break

                finMenu = True
                return finMenu

            except IceFlix.TemporaryUnavailable:

                if numIntentos >= INTENTOS_MAX:
                    print(
                        f"-> Service Error. WARNING: All connection attempts have been spent\n")

                    validUpdate = False
                    return validUpdate

                else:

                    print(f"-> Service Error, restarting connection.\n")

                numIntentos = numIntentos + 1
                pass

            except IceFlix.Unauthorized:

                print(f"-> Error, you do not have correct authorization\n")

                validUpdate = False
                return validUpdate

            except IceFlix.WrongMediaId:

                print(f"-> Error, file not found\n")

                validUpdate = False
                return validUpdate

            except IceFlix.UploadError:

                print(f"-> Error uploading file\n")

                validUpdate = False
                return validUpdate

            except Exception as error:

                print(error)

                validUpdate = False
                return validUpdate

    def menuAdministrativo(self, proxyPrincipal):

        numIntentos = 0
        finMenu = False
        validUpdate = True
        global tknUsuario

        properties = Ice.createProperties()
        properties.load("./configs/cli.conf")
        ADMIN_TOKEN = properties.getProperty("cli.admin_token")

        while not numIntentos >= INTENTOS_MAX:

            try:
                print("What would you like to do?\n")

                print(" 1 - Add User\n")
                print(" 2 - Delete User\n")

                option = input(
                    "-> Enter the number corresponding to the desired option: \n ")
                option = int(option)

                if option == 1:

                    '''Aniadir Usuario'''

                    userAdd = input("Enter Username: ")
                    contrasena = getpass.getpass(f"Enter Password: ")
                    contra = hashlib.sha256(contrasena.encode())

                    proxyAuth = proxyPrincipal.getAuthenticator()
                    proxyAuth.addUser(userAdd, contra.hexdigest(), ADMIN_TOKEN)
                    print("User added successfully")

                elif option == 2:

                    '''Borrar Usuario'''

                    userDel = input("Enter Username: ")

                    proxyAuth = proxyPrincipal.getAuthenticator()
                    proxyAuth.removeUser(userDel, ADMIN_TOKEN)
                    print("User deleted successfully")

                else:

                    print(f"-> Error, you have selected an invalid option\n")
                    break

                finMenu = True
                return finMenu

            except IceFlix.TemporaryUnavailable:

                if numIntentos >= INTENTOS_MAX:
                    print(
                        f"-> Service Error. WARNING: All connection attempts have been spent\n")

                    validUpdate = False
                    return validUpdate

                else:

                    print(f"-> Service Error, restarting connection.\n")

                numIntentos = numIntentos + 1
                pass

            except IceFlix.Unauthorized:

                print(f"-> Error, you do not have correct authorization\n")

                validUpdate = False
                return validUpdate

            except Exception as error:

                print("Exception, the update has not been successful")

                validUpdate = False
                return validUpdate

    def establecer_conexion(self):

        proxyPrincipal = self.connect()

        if proxyPrincipal:
            self.connected = True
            print(f"-> The connection is established. \n")
            return proxyPrincipal

    def menu_registrado(self, proxyPrincipal):

        global tknUsuario

        if proxyPrincipal:

            print("-> Connection established successfully. \n")
        print("-> TOKEN OF THE USER: {} \n".format(tknUsuario))
        print("-> YOUR USERNAME: {} \n".format(self.nameUser))

        print(f"\r --------------------MAIN MENU--------------------- \n")

        print(f"-> Please, select the desired option: \n")

        print(f"\r 1 - Establish connection \n")
        print(f"\r 2 - Login \n")
        print(f"\r 3 - Logout \n")
        print(f"\r 4 - Administrative Options \n")
        print(f"\r 5 - Video streaming \n")
        print(f"\r 6 - Search from our catalog \n")
        print(f"\r 7 - Modify data from our catalog \n")
        print(f"\r 8 - Exit application \n")

    def menu_inicial(self, proxyPrincipal):

        if proxyPrincipal:

            print("-> Connection established successfully. \n")

        print(f"\r --------------------MAIN MENU--------------------- \n")

        print(f"-> Please, select the desired option: \n")

        print(f"\r 1 - Establish connection \n")
        print(f"\r 2 - Login \n")
        print(f"\r 3 - Search from our catalog \n")
        print(f"\r 4 - Exit application \n")

    def autenticarse(self, proxyPrincipal, adminTopic, noLogeado, intento): 

        stop = False

        if noLogeado == True and self.connected:

            answer, nameUser, pswd = self.login(proxyPrincipal)

            if answer == True:

                topicRevoc = topic_management.obtainTopic(
                    adminTopic, 'Revocations')
                revocations = Revocations(proxyPrincipal, nameUser, pswd)
                self.prxRevoc = self.adapter.addWithUUID(revocations)
                proxy=IceFlix.RevocationsPrx.checkedCast(self.prxRevoc)
                topicRevoc.subscribeAndGetPublisher({}, proxy)
                self.intento = 0
                noLogeado = False

            elif answer == False and self.intento <= 3:

                topicRevoc = topic_management.obtainTopic(
                adminTopic, 'Revocations')
                revocations = Revocations(proxyPrincipal, nameUser, pswd)
                prxRevoc = self.adapter.addWithUUID(revocations)
                topicRevoc.subscribeAndGetPublisher({}, prxRevoc)
                
                noLogeado = True
                self.intento += 1
                print("-> User authentication attempt number: " + str(self.intento))

                if self.intento == 3:

                    print("Sorry, you have exceeded the maximum number of authentication attempts.")
                    stop = True

            
            else:
                stop = True

        else:
            print(f"-> Error, please, connect to the main proxy before continuing. \n")

        return noLogeado,stop

    def cerrarSesion(self,adminTopic, noLogeado):

        if noLogeado == False and self.connected:

            topicRevoc = topic_management.obtainTopic(
                adminTopic, 'Revocations')
            proxy=IceFlix.RevocationsPrx.checkedCast(self.prxRevoc)
            topicRevoc.unsubscribe(proxy)

            tknUsuario = ""
            self.nameUser = ""

            noLogeado = True

        else:

            print(f"-> Error, please, connect to the main proxy before continuing. \n")

        return noLogeado

    def run(self, argv):

        global ADMIN_TOKEN
        properties = Ice.createProperties()
        properties.load("./configs/cli.conf")
        ADMIN_TOKEN = properties.getProperty("cli.admin_token")
        msgBroker = self.communicator()
        global tknUsuario
        global intento

        proxyPrincipal = None
        noLogeado = True



        self.adapter = msgBroker.createObjectAdapterWithEndpoints(
            'MediaUploaderAdapter', 'tcp')
        self.adapter.activate()
        print("El admin token es {}".format(str(ADMIN_TOKEN)))
        adminTopic = topic_management.obtainManager(self.communicator())
        numIntentos = 0
       
       
        while numIntentos < INTENTOS_MAX:

            try:

                if noLogeado == False:

                    self.menu_registrado(proxyPrincipal)
                    option = int(
                        input(f"-> Enter the number corresponding to the desired option: "))

                    print("\n")
                    if option == 1:
                        proxyPrincipal = self.establecer_conexion()

                    elif option == 2:
                       
                       noLogeado,stop=self.autenticarse(proxyPrincipal,adminTopic,noLogeado, self.intento)
                       if stop: 
                        break

                    elif option == 3:

                        noLogeado=self.cerrarSesion(adminTopic,noLogeado)
                        print()

                    elif option == 4:

                        self.menuAdministrativo(proxyPrincipal)

                    elif option == 5:

                        if not self.connected:
                            print(f"-> Error, please, connect to the main proxy and the Stream Provider before continuing. \n")
                        else:
                            self.mediaStreaming(
                                msgBroker, proxyPrincipal, tknUsuario)

                    elif option == 6:

                        if not self.connected:

                            print(f"-> Error, please, connect to the main proxy before continuing. \n")

                        else:  self.catalogSearch(proxyPrincipal)

                    elif option == 7:

                        if not self.connected:

                            print(
                                f"-> Error, please, connect to the main proxy and the Stream Provider before continuing. \n")

                        else:

                            self.catalogUpdate(proxyPrincipal)

                    elif option == 8:

                        print(
                            f"-> Logging out, thank you very much for using our services. \n")
                        break

                    else:
                        break

                else:

                    self.menu_inicial(proxyPrincipal)
                    option = int(
                        input(f"-> Enter the number corresponding to the desired option: "))

                    print("\n")
                    if option == 1:

                        proxyPrincipal = self.establecer_conexion()

                    elif option == 2:
                         noLogeado,stop=self.autenticarse(proxyPrincipal,adminTopic,noLogeado, self.intento)
                         if stop:
                            break
                       
                    elif option == 3:

                        if not self.connected:

                            print(
                                f"-> Error, please, connect to the main proxy before continuing. \n")

                        else:

                            self.catalogSearch(proxyPrincipal)

                    elif option == 4:

                        print(
                            f"-> Logging out, thank you very much for using our services. \n")
                        break

                    else:
                        break

            except IceFlix.TemporaryUnavailable:

                if numIntentos >= INTENTOS_MAX:

                    print(
                        f"-> Service Error. WARNING: All connection attempts have been spent\n")
                    sys.exit(1)

                else:

                    print(f"-> Service Error, restarting connection.\n")

                numIntentos = numIntentos + 1

                time.sleep(12)

            except Exception as error:

                print(error)
                pass

        return 0


continuar = True


class StreamSync(IceFlix.StreamSync):

    def __init__(self, proxyStream_sync, proxy_controller, proxyAuthentication, nameUser, pswd):

        self.proxyAuth = proxyAuthentication
        self.nameUser = nameUser
        self.pswd = pswd
        self.proxyStream_sync = proxyStream_sync
        self.controlador = proxy_controller

    def requestAuthentication(self, current=None):

        global continuar
        global tknUsuario

        invalid = True
        continuar = True

        try:

            threading.Thread(target=self.temporizador).start() #empieza a contar desde que se lanza
            while continuar == True:

                try:

                    tokenCreated = self.proxyAuth.refreshAuthorization(
                        self.nameUser, self.pswd)

                    if tokenCreated is not None:

                        invalid = not self.proxyAuth.isAuthorized(tokenCreated)

                        if not invalid:

                            self.controlador.refreshAuthentication(
                                tokenCreated)
    

                            break

                except IceFlix.Unauthorized:

                    continue

        except Exception:

            continuar = False

        if invalid == False:

            tknUsuario = tokenCreated

        if invalid == True and continuar == False:

            self.proxyStream_sync.suprimirDatos() #rompe conexion

    def temporizador(self):

        global continuar

        while True:

            time.sleep(5)
            continuar = False


class Revocations(IceFlix.Revocations):  # cambiada sintaxis para adecuarse a interfaz

    def __init__(self, proxyPrincipal, nameUser, pswd):

        self.nameUser = nameUser
        self.pswd = pswd
        self.proxyPrincipal = proxyPrincipal

    def revokeUser(self, user, srvId, current=None):
        # incluido en la interfaz
        return 0

    def revokeToken(self, tknUser, servicio, current=None):

        global tknUsuario

        if tknUsuario == tknUser:

            proxyAuth = self.proxyPrincipal.getAuthenticator()
            tknUsuario = proxyAuth.refreshAuthorization(
                self.nameUser, self.pswd)


class MediaUploader(IceFlix.MediaUploader):

    def __init__(self, nameArchivo):

        if(isfile(nameArchivo)):

            self._file_ = nameArchivo
            self._fd_ = open(self._file_, 'rb')

        else:

            print("Not found: {}".format(nameArchivo))

    def close(self, current=None):

        self._fd_.close()

    def suprimirDatos(self, current):

        try:

            current.adapter.remove(current.identifier)

        except Exception as error:

            print("Error, it has not been removed correctly")

    def receive(self, size, current):

        try:

            readResults = self._fd_.read(size)
            return readResults

        except Exception as error:

            print("Error, the data has not been received correctly")


sys.exit(Client().main(sys.argv))
