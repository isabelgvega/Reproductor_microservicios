#!/usr/bin/env python3


import Ice
import topic_management
import IceStorm
import time
import random
import threading
import sqlite3
import os
import json
import uuid
import sys
import json
import logging

Ice.loadSlice('./iceflix.ice')

import IceFlix
CREAR = True
media = {}
main_servers = {}
streamings = {}
mediacatalogs = {}
actualizado = False
DATABASE = './data/catalogo.db'

# Clases custom de la interfaz iceflix.ice


class Media(IceFlix.Media):

    def __init__(self, mediaId, provider, info):

        self.mediaId = mediaId
        self.provider = provider
        self.info = info


class MediaInfo(IceFlix.MediaInfo):

    def __init__(self, name, tags):

        self.name = name
        self.tags = tags


class MediaDB(IceFlix.MediaDB):

    def __init__(self, mediaId, name, tagsPerUser):

        self.mediaId = mediaId
        self.name = name
        self.tagsPerUser = tagsPerUser


class CatalogUpdates(IceFlix.CatalogUpdates):

    def __init__(self, parent, uuid):

        self.id = uuid
        self.padre = parent

    # habria que probar funcionamiento con varias instancias
    def renameTile(self, mediaId, name,srvId, current=None):       #quitar sverid
          # si fuese el mismo id, provoca bloqueo
          if srvId!=self.id:
            print("[CATALOGO]: Emitted renameTile, from {}".format(srvId))
            if mediaId in media:
                media[mediaId]['nombre_inicial'] = name
            ok = self.padre.catalogo.renameTile(mediaId,name)
            if ok == False:
                raise IceFlix.WrongMediaId()

    def addTags(self, mediaId, tags, user, srvId, current=None):
       
        if srvId != self.id:
            print("[CATALOGO]: Emitted addTags, from: {}".format(srvId))
            autorizado = self.parent.getAuth().isAuthorized(user)
            if autorizado:
                nombre_usuario = self.parent.getAuth().whois(user)
                resultado = self.parent.catalogo.addTags(mediaId, nombre_usuario, tags)
                if resultado == False:
                    raise IceFlix.WrongMediaId()

    def removeTags(self, mediaId, tags, user, srvId, current=None):

        if srvId != self.id:
            print("[CATALOGO]: Emitted removeTags from {}".format(srvId))
            autorizado = self.parent.getAuth().isAuthorized(user)
            if autorizado:
                nombre_usuario = self.parent.getAuth().whois(user)
                resultado = self.parent.catalogo.removeTags(
                    mediaId, nombre_usuario, tags)
                if resultado == False:
                    raise IceFlix.WrongMediaId()


class Catalogo():  # puede que se cambie a json

    def __init__(self):

        global DATABASE
        if not os.path.exists(DATABASE):  # si no existe la bd la creamos
            conexion = self.conectar()
            self.crear_tablas(conexion)

    def conectar(self):

        global DATABASE
        try:
            conexion = sqlite3.connect(DATABASE)
            return conexion
        except Exception as Error:
            print(Error)

    def crear_tablas(self, conexion):

        objeto_tabla = conexion.cursor()
        objeto_tabla.execute("CREATE TABLE Tags(tag text PRIMARY KEY)")
        objeto_tabla.execute(
            "CREATE TABLE Usuarios(ID text PRIMARY KEY, Nombre text)")
        self.cargar_usuarios(conexion)
        objeto_tabla.execute(
            "CREATE TABLE Medios(ID text PRIMARY KEY, Nombre text)")
        objeto_tabla.execute(
            "CREATE TABLE Catalogo(ID text PRIMARY KEY, Id_video text , Id_usuario text , Tag text)")

        conexion.commit()
        conexion.close()


    def cargar_usuarios(self,conexion):
        id=0
        objeto_tabla = conexion.cursor()
        with open('./data/users.json') as json_file:
            data = json.load(json_file)
        for key in data:
          sql_query = '''INSERT INTO Usuarios(ID,Nombre) VALUES (?, ?)'''
          nombre=key
          sql_data = (id,nombre)
          objeto_tabla.execute(sql_query, sql_data)
          id=id+1
          conexion.commit()

    

    def removeTile(self,mediaId):
        self._con_ = self.conectar()
        con_obj = self._con_.cursor()

        sqlCatalogo = "DELETE FROM Catalogo WHERE Id_video=?"
        sqlPeli = "DELETE FROM Medios WHERE ID=?" #revisar

        sqlDatos = (mediaId)
        con_obj.execute(sqlCatalogo, (sqlDatos,))
        con_obj.execute(sqlPeli, (sqlDatos,))

        self._con_.commit()
        self._con_.close()
        
    def videoInDB(self, nombre_video):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT ID FROM Medios WHERE Nombre=?'''
        sql_data = (nombre_video)
        objeto_tabla.execute(sql_query, (sql_data,))
        entry = objeto_tabla.fetchone()
        if entry:
            conexion.close()
            return True
        else:
            conexion.close()
            return False

    def CatalogInDB(self, media_Id, user_id, tag):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT * FROM Catalogo WHERE Id_video=? AND Id_usuario=? AND tag=?'''
        sql_data = (media_Id, user_id, tag)
        objeto_tabla.execute(sql_query, sql_data)
        entry = objeto_tabla.fetchone()
        if entry:
            conexion.close()
            return True
        else:
            conexion.close()
            return False

    def tagInDB(self, tag):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT * FROM Tags WHERE tag=?'''
        sql_data = (tag)
        objeto_tabla.execute(sql_query, (sql_data,))
        entry = objeto_tabla.fetchone()
        if entry:
            conexion.close()
            return True
        else:
            conexion.close()
            return False

    def userInDB(self, user_name):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT ID FROM Usuarios WHERE Nombre=?'''
        sql_data = (user_name)
        objeto_tabla.execute(sql_query, (sql_data,))
        entry = objeto_tabla.fetchone()
        if entry:
            conexion.close()
            return entry[0]
        else:
            conexion.close()
            return False

    def crearTag(self, tag):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''INSERT INTO Tags(tag) VALUES (?)'''
        sql_data = (tag)
        objeto_tabla.execute(sql_query, (sql_data,))
        conexion.commit()
        conexion.close()

    def crearCatalogEntry(self, media_Id, user_id, tag):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''INSERT INTO Catalogo(Id_video, Id_usuario, Tag) VALUES (?, ?, ?)'''
        sql_data = (media_Id, user_id, tag)
        objeto_tabla.execute(sql_query, sql_data)
        conexion.commit()
        conexion.close()

    def crearUsuario(self, user_name, user_id):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''INSERT INTO Usuarios(ID, Nombre) VALUES (?, ?)'''
        sql_data = (user_id, user_name)
        objeto_tabla.execute(sql_query, (sql_data))
        conexion.commit()
        conexion.close()

    def getUserbyId(self, user_id):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT Nombre FROM Usuarios WHERE ID=?'''
        sql_data = (user_id)
        objeto_tabla.execute(sql_query, (sql_data,))
        nombre = objeto_tabla.fetchone()
        conexion.close()
        return nombre[0]

    def getMediaDBList(self):

        lista_bd = []
        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT * FROM Medios'''
        objeto_tabla.execute(sql_query)
        videos = objeto_tabla.fetchall()
        for video in videos:
            tagsPerUser = {}
            # primero obtenemos el nombre de la peli
            media_Id = video[0]
            name = video[1]
            # obtenemos los usuarios de ese video
            sql_query = '''SELECT DISTINCT Id_usuario FROM Catalogo WHERE Id_video=?'''
            sql_data = (media_Id)
            objeto_tabla.execute(sql_query, (sql_data,))
            usuarios = objeto_tabla.fetchall()
            for user in usuarios:
                lista_tags = []
                # miramos los tags de cada usuario
                sql_query = '''SELECT Tag FROM Catalogo WHERE Id_video=? AND Id_usuario=?'''
                sql_data = (media_Id, user[0])
                objeto_tabla.execute(sql_query, sql_data)
                tags = objeto_tabla.fetchall()
                for tag in tags:
                    lista_tags.append(tag[0])

                # añadimos a tagsperuser lost tags de cada usuario
                print("EL nombre de usuario es {}".format(user[0]))
                nombre_usuario = self.getUserbyId(user[0])
                tagsPerUser[nombre_usuario] = lista_tags

            # insertamos en la lista a devolver el objeto MediaDB
            lista_bd.append(MediaDB(media_Id, name, tagsPerUser))

        conexion.close()
        return lista_bd

    def getTags(self, id_film, id_user):

        tags = []
        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT * FROM Catalogo WHERE Id_video=? AND Id_usuario=?'''
        sql_data = (id_film, id_user)
        objeto_tabla.execute(sql_query, sql_data)
        entradas_tags = objeto_tabla.fetchall()
        for tag in entradas_tags:
            tags.append(tag[0])
        conexion.close()
        return tags

    def getVideoTitle(self, mediaId):

        con = self.conectar()
        cObj = con.cursor()
        sql = '''SELECT Nombre FROM Medios WHERE ID=?'''
        sql_data = (mediaId)
        cObj.execute(sql, (sql_data,))
        row = cObj.fetchone()
        con.close()
        return row[0]

    def crearTile(self, mediaId, name):

        print("[CATALOGO]: Añadir tile...")

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''INSERT INTO Medios(ID, Nombre) VALUES (?, ?)'''
        sql_data = (mediaId, name)
        objeto_tabla.execute(sql_query, sql_data)
        conexion.commit()
        conexion.close()

    def vidInDB(self, mediaId):  # checkea si la id de un video esta en la db
        
        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT * FROM Medios WHERE ID=?'''
        sql_data = (mediaId)
        objeto_tabla.execute(sql_query, (sql_data,))
        entry = objeto_tabla.fetchall()
        if entry:
            conexion.close()
            return True
        else:
            conexion.close()
            return False

    def getTilesByName(self, name, exact):

        conexion = self.conectar()

        tiles = []
        nombre_mayus = name.upper()  # CREO QUE NO HACE FALTA
        objeto_tabla = conexion.cursor()
        if(exact):
            sql_query = '''SELECT * FROM Medios WHERE UPPER(Nombre) LIKE ?'''
            objeto_tabla.execute(sql_query, (nombre_mayus,))
            entries = objeto_tabla.fetchall()
            if entries:
                for entry in entries:
                    tiles.append(entry)
            else:
                print("[CATALOGO]: Pelicula no encontrada")

        else:
            sql_query = '''SELECT * FROM Medios WHERE (INSTR(UPPER(Nombre), ?) > 0)'''  # instr=contiene ?
            objeto_tabla.execute(sql_query, (nombre_mayus,))
            entries = objeto_tabla.fetchall()
            if entries:
                for entry in entries:
                    tiles.append(entry)
            else:
                print("[CATALOGO]: Pelicula no encontrada")

        conexion.close()
        return tiles

    def addTags(self, mediaId, username, tags):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT * FROM Medios WHERE ID LIKE ?'''
        id_mayus = mediaId.upper()
        objeto_tabla.execute(sql_query, (id_mayus,))
        entry = objeto_tabla.fetchone()
        if not entry:
            conexion.close()
            return False
        else:
            for tag in tags:
                tag_mayus = tag.upper()
                sql_query = '''SELECT tag FROM Tags WHERE UPPER(tag) = ?'''
                objeto_tabla.execute(sql_query, (tag_mayus,))
                entry = objeto_tabla.fetchone()
                if not entry:
                    sql_insert_query = '''INSERT INTO Tags VALUES (?)'''
                    objeto_tabla.execute(sql_insert_query, (tag,))
                    conexion.commit()
                # sacamos el id del usuario
                sql_query = '''SELECT ID FROM Usuarios WHERE UPPER(Nombre) = ?'''
                username_mayus = username.upper()
                objeto_tabla.execute(sql_query, (username_mayus,))
                usuario = objeto_tabla.fetchone()
                print("[CATALOGO]: EL usuario es {}, el username es:{}".format(usuario,username_mayus))
                id_usuario = usuario[0]
                sql_query = '''INSERT INTO Catalogo(Id_video, Id_usuario, Tag) VALUES (?, ?, ?)'''
                sql_data = (mediaId, id_usuario, tag)
                objeto_tabla.execute(sql_query, sql_data)
                conexion.commit()
            conexion.close()

            return True

    def removeTags(self, mediaId, username, tags):

        conexion = self.conectar()
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT ID FROM Usuarios WHERE UPPER(Nombre) = ?'''
        nombre_mayus = username.upper()
        objeto_tabla.execute(sql_query, (nombre_mayus,))
        entry = objeto_tabla.fetchone()
        userId = entry[0]
        for tag in tags:
            tag_mayus = tag.upper()

            sql_query = '''DELETE FROM Catalogo WHERE Id_video=? AND Id_usuario=? AND UPPER(Tag) LIKE ?'''
            sql_data = (mediaId, userId, tag_mayus)
            objeto_tabla.execute(sql_query, sql_data)
            conexion.commit()
            print("[CATALOGO]: Tag eliminado")
        conexion.close()

    def getTilesByTags(self, tags, username, includeAllTags):

        conexion = self.conectar()

        tiles = []
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT ID FROM Usuarios WHERE UPPER(Nombre) = ?'''
        nombre_mayus = username.upper()
        objeto_tabla.execute(sql_query, (nombre_mayus,))
        entry = objeto_tabla.fetchone()
        userId = entry[0]

        if includeAllTags:
            tiles_id = []
            for tag in tags:  # para cada tag pasado por parametro
                lista_aux = []
                lista_final = []
                sql_query = '''SELECT Id_video FROM Catalogo WHERE Tag=? AND Id_usuario=?'''  # seleccion entradas de catalogo con ese tag y ese user
                sql_data = (tag, userId)
                objeto_tabla.execute(sql_query, sql_data)
                entries = objeto_tabla.fetchall()
                if not entries:
                    print("[CATALOGO]: No existen medios con estos tags")
                    tiles_id = []
                    break
                else:
                    for i in range(0, len(entries), 1):
                        # si la entrada no esta en aux lo mete
                        if entries[i][0] not in lista_aux:
                            lista_aux.append(str(entries[i][0]))
                    if len(tiles_id) < 1:
                        lista_final = lista_aux  # si tilesid esta vacia se añaden todos los films con cada tag
                    else:  # si ya contiene los films que contiene un tag comprueba cuales son iguales a los que contienen el otro tag y los añade a la lista final para sobreescribir tiles_id
                        for tileId in tiles_id:
                            if tileId in lista_aux:
                                lista_final.append(tileId)
                    tiles_id = lista_final
            if tiles_id:  # sino esta vacia
                for tileId in tiles_id:
                    sql_query = '''SELECT * FROM Medios WHERE ID=?'''
                    objeto_tabla.execute(sql_query, (tileId,))
                    entries = objeto_tabla.fetchall()
                    for entry in entries:
                        tiles.append(entry)

        else:
            tiles_id = []
            for tag in tags:
                sql = '''SELECT Id_video FROM Catalogo WHERE Tag=? AND Id_usuario=?'''
                sql_data = (tag, userId)
                objeto_tabla.execute(sql, sql_data)
                entries = objeto_tabla.fetchall()
                if entries:
                    for i in range(0, len(entries), 1):
                        tiles_id.append(str(entries[i][0]))
            if tiles_id:
                for tileId in tiles_id:
                    sql_query = '''SELECT * FROM Medios WHERE ID=?'''
                    objeto_tabla.execute(sql_query, (tileId,))
                    entries = objeto_tabla.fetchall()
                    for entry in entries:
                        tiles.append(entry)

        conexion.close()
        return tiles

    def renameTile(self, mediaId, name):

        conexion = self.conectar()
        ok = False
        objeto_tabla = conexion.cursor()
        sql_query = '''SELECT ID FROM Medios WHERE ID LIKE ?'''
        objeto_tabla.execute(sql_query, (mediaId,))
        entries = objeto_tabla.fetchall()
        if entries:
            sql_query = '''UPDATE Medios SET Nombre=? WHERE ID=?'''
            sql_data = (name, mediaId)
            objeto_tabla.execute(sql_query, sql_data)
            conexion.commit()
            ok = True
        conexion.close()
        return ok


class MediaCatalog(IceFlix.MediaCatalog):

    def __init__(self, adapter, broker, topic_manager, id):

        self._broker_ = broker
        self.id = id
        self.topic_manager = topic_manager
        self.CU_topic = topic_management.obtainTopic(
            self.topic_manager, 'CatalogUpdates')
        self.catalogUpdates = CatalogUpdates(self, self.id)
        self.CU_proxy = adapter.addWithUUID(self.catalogUpdates)
        self.CU_topic.subscribeAndGetPublisher({}, self.CU_proxy)

        self.catalogo = Catalogo()

    def getCatalogUpdates(self):
        publisher = self.CU_topic.getPublisher()
        CatalogUpdates_proxy = IceFlix.CatalogUpdatesPrx.uncheckedCast(publisher)
        return CatalogUpdates_proxy

    def getMain(self):

        global main_servers
        main_proxy = random.choice(list(main_servers.values()))
        return IceFlix.MainPrx.uncheckedCast(main_proxy)

    def getAuth(self):

        main = self.getMain()
        return main.getAuthenticator()

    def getTile(self, mediaId, userToken, current = None):

        global streamings
        global media
        print("[CATALOGO]: Obteniendo la información del medio id="+mediaId+"...")

        if self.getAuth().isAuthorized(userToken) == False:
            raise IceFlix.Unauthorized()

        if mediaId in media:
            media_encontrado = True  # esta en buffer de catalogo
            print("[CATALOGO]: Video dentro del buffer de catalogo")
        else:
            media_encontrado = False

        if self.catalogo.vidInDB(mediaId):
            media_encontrado_db = True  # esta en la base de datos
            print("[CATALOGO]: Video dentro de la base de datos del catalogo")
        else:
            print("[CATALOGO]: El video no se encuentra en la base de datos")
            media_encontrado_db = False

        if media_encontrado_db == True and media_encontrado == False:

            raise IceFlix.TemporaryUnavailable()
        elif media_encontrado_db == False and media_encontrado == False:
            
            raise IceFlix.WrongMediaId()

        else:
            user_id = self.getAuth().whois(userToken)  # se obtiene el stringlist
            tags = self.catalogo.getTags(mediaId, user_id)
            nombre = self.catalogo.getVideoTitle(mediaId)
            info = MediaInfo(nombre, tags)  # Construimos estructura MediaInfo
            # cualquier stream provider
            
            stream_proxy = str(media[mediaId]['provider'])
            print("CATALOGO: STREAM_PRLOXY={}".format(stream_proxy))
            stream_provider = IceFlix.StreamProviderPrx.checkedCast(
                self._broker_.stringToProxy(stream_proxy))
            new_media = Media(mediaId, stream_provider, info)
            return new_media

    def getTilesByName(self, name, exact, current=None):

        lista_titulos = self.catalogo.getTilesByName(name, exact)
        string_resultados = ', '.join(map(str, lista_titulos))
        return string_resultados

    def getTilesByTags(self, tags, includeAllTags, userToken, current=None):

        # siempre se comprueba que el usuario esta autorizado
        print("[CATALOGO] El token que se envia para comprobar autorización es: {}".format(userToken))
        autorizado = self.getAuth().isAuthorized(userToken)
        print("[CATALOGO] El token que se envia para comprobar autorización es: {} y se recibe {}".format(userToken,autorizado))
        if autorizado:
            nombre_usuario = self.getAuth().whois(userToken)
            lista_titulos = self.catalogo.getTilesByTags(
                tags, nombre_usuario, includeAllTags)

            string_resultados = ', '.join(
                map(str, lista_titulos))  # funcion map=iterador que convierte lista_titulos en string para imprimir, join las va concatenando
            return string_resultados
        else:
            raise IceFlix.Unauthorized()

    def addTags(self, mediaId, tags, userToken, current=None):

        # cromprobación de userToken
        autorizado = self.getAuth().isAuthorized(userToken)
        if not autorizado:
            raise IceFlix.Unauthorized()
        else:
            nombre_usuario = self.getAuth().whois(userToken)
            ok = self.catalogo.addTags(mediaId, nombre_usuario, tags)
            if ok == False:
                raise IceFlix.WrongMediaId()

            else:
                catalogUpdates = self.getCatalogUpdates()
                catalogUpdates.addTags(mediaId, tags, nombre_usuario, self.id)

    def renameTile(self, mediaId, name, adminToken, current = None):

        # Comprobación de userToken
        global media
        autorizado = self.getMain().isAdmin(adminToken)
        if autorizado:
            if mediaId in media:
                media[mediaId]['nombre_inicial'] = name
            resultado = self.catalogo.renameTile(mediaId, name)
            if resultado == False:
                raise IceFlix.WrongMediaId()
            else:
                catalogUpdates = self.getCatalogUpdates()
                catalogUpdates.renameTile(mediaId, name, self.id)

        else:
            raise IceFlix.Unauthorized()

    def removeTags(self, mediaId, tags, userToken, current=None):

        # cromprobación de userToken
        autorizado = self.getAuth().isAuthorized(userToken)
        if not autorizado:
            raise IceFlix.Unauthorized()
        else:
            nombre_usuario = self.getAuth().whois(userToken)
            resultado = self.catalogo.removeTags(mediaId, nombre_usuario, tags)
            if resultado == False:
                raise IceFlix.WrongMediaId()
            else:
                catalogUpdates = self.getCatalogUpdates()
                catalogUpdates.removeTags(mediaId, tags, nombre_usuario, self.id)

    def getMediaDBList(self):

        lista_bd = []
        lista_bd = self.catalogo.getMediaDBList()
        return lista_bd

    def updateDB(self, catalogDatabase, srvId, current=None):

        global media
        global actualizado
        if actualizado == False:
            actualizado = True
            print("[CATALOGO]: Actualizando BD...")
            if srvId not in mediacatalogs.keys():
                raise IceFlix.UnknownService

            if srvId != self.id:
                for video in catalogDatabase:
                    mediaId = video.mediaId
                    nombre_media = video.name
                    tagsPerUser = video.tagsPerUser

                    # no existe el medio
                    if not self.catalogo.videoInDB(nombre_media):
                        self.catalogo.crearTile(mediaId, nombre_media)

                    for nombre_usuario, tags in tagsPerUser.items():
                        user_id = 0
                        if not self.catalogo.userInDB(nombre_usuario):
                            self.catalogo.crearUsuario(nombre_usuario, user_id)

                        for tag in tags:
                            # no esta en la tabla tag de la bd
                            if not self.catalogo.tagInDB(tag):
                                self.catalogo.crearTag(tag)
                                self.catalogo.crearCatalogEntry(
                                    mediaId, user_id, tag)
                            else:
                                if not self.catalogo.CatalogInDB(mediaId, user_id, tag):
                                    self.catalogo.crearCatalogEntry(
                                        mediaId, user_id, tag)

                        # user id empezara en 0 e ira aumentado progresivamente seguns e añaden users
                        user_id = user_id + 1
            print("[CATALOGO]: La base de datos ha sido actualizada...")


class Server(Ice.Application):

    def run(self, argv):
        global DATABASE

        print('Iniciando servidor catalogo')

        broker = self.communicator()

        adapter = broker.createObjectAdapterWithEndpoints(
            'CatalogAdapter', 'tcp')
        adapter.activate()

        topic_manager = topic_management.obtainManager(self.communicator())

        srvId = str(uuid.uuid4())
        servant = MediaCatalog(adapter, broker, topic_manager, srvId)
        proxy = adapter.addWithUUID(servant)
        time.sleep(3)
        while(os.path.exists(DATABASE) == False):
            pass
         # hasta que no se crea la base da datos no avanza
        sa_topic = topic_management.obtainTopic(
            topic_manager, 'StreamAnnouncements')
        sa = StreamAnnouncements(servant)

        sa_proxy = adapter.addWithUUID(sa)
        sa_topic.subscribeAndGetPublisher({}, sa_proxy)

        announce_topic = topic_management.obtainTopic(
            topic_manager, 'ServiceAnnouncements')

        announce = ServiceAnnouncements(srvId, servant)
        announce_proxy = adapter.addWithUUID(announce)

        announce_topic.subscribeAndGetPublisher({}, announce_proxy)
        time.sleep(11)

        try:
            threading.Thread(
                target=self.lanzando_threads,
                args=(
                    announce_topic,
                    proxy,
                    srvId,
                ),
            ).start()

        except Exception as e:
            print(e)
        print('Servidor en ejecución...')
        print('"{}"'.format(proxy), flush=True)
        self.shutdownOnInterrupt()
        broker.waitForShutdown()

        return 0

    def lanzando_threads(self, as_topic, serv, srvId):

        time.sleep(2)
        publicador = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(
            as_topic.getPublisher())

        publicador.newService(serv, srvId)

        while True:

            publicador = IceFlix.ServiceAnnouncementsPrx.uncheckedCast(
                as_topic.getPublisher())
            publicador.announce(serv, srvId)
            time.sleep(8)


class StreamAnnouncements(IceFlix.StreamAnnouncements):

    def __init__(self, servidor):

        self.servidor_catalogo = servidor

    def newMedia(self, mediaId, initialName, srvId, current=None):

        global media
        global streamings

        print("[CATALOGO]: Añadiendo archivo a DB".format(initialName))
        persistente = self.servidor_catalogo.catalogo.vidInDB(mediaId)
        if persistente:
            provider=''
            if mediaId not in media:

                print("[CATALOGO]:Persistente- El provider es {}".format(provider))
                data = {
                    'nombre': initialName,
                    'provider': self.getProvider(srvId)
                }
                media[mediaId] = data

        else:
            self.servidor_catalogo.catalogo.crearTile(mediaId, initialName)
            provider=''

            print("[CATALOGO]:No Persistente- El provider es {}".format(provider))
            data = {
                'nombre': initialName,
                'provider': self.getProvider(srvId)
            }
            media[mediaId] = data

    def getProvider(self, srvId):

        global streamings

        for id in streamings.keys():

            if id == srvId:

                print(streamings[id])
                return streamings[id]


    def removedMedia(self, mediaId, srvId, current=None):

        global media
        self.servidor_catalogo.catalogo.removeTile(mediaId)
        print("[CATALOGO]: Emitted removedMedia from {}".format(srvId))
        if mediaId in media:
            del media[mediaId]


class ServiceAnnouncements(IceFlix.ServiceAnnouncements):

    def __init__(self, own_service_id, own_servant):

        self.service_id = own_service_id
        self.servant = own_servant

    def newService(self, service, service_id, current=None):

        global streamings
        global main_servers
        global mediacatalogs

        if service_id == self.service_id:
         logging.debug("Received own announcement. Ignoring")
         return

        else:
            proxy = IceFlix.MediaCatalogPrx.checkedCast(service)

            if not proxy:
                logging.debug("New service isn't of my type. Ignoring") 

            elif service_id not in mediacatalogs:

                    print("[CATALOGO]: Emitted newService from {}".format(service_id))
                    mediacatalogs[service_id] = IceFlix.MediaCatalogPrx.uncheckedCast(
                        service)
                    if not len(mediacatalogs) <= 0:          #share_data_with
                        print(
                            "A new service has been created ::IceFlix::MediaCatalog ", flush=True)
                        mediaDBList = self.servant.getMediaDBList()
                        nuevo_catalogo = IceFlix.MediaCatalogPrx.uncheckedCast(
                            service)
                        nuevo_catalogo.updateDB(mediaDBList, self.service_id)
                        print("[CATALOGO]: UpdatedDB hecho")

            #comprueba si es un streamprovider            
            proxy = IceFlix.StreamProviderPrx.checkedCast(service) 

            if not proxy:
                logging.debug("New service isn't of my type. Ignoring")
                return
            elif service_id not in streamings:
                    print("[CATALOGO]: A new service has been created ::IceFlix::StreamProvider ", flush=True)
                    streamings[service_id] = IceFlix.StreamProviderPrx.uncheckedCast(
                        service)
                    if not len(streamings) <= 1:
                        stream_provider = IceFlix.StreamProviderPrx.uncheckedCast(
                            service)
                        stream_provider.reannounceMedia(self.service_id)

    def announce(self, service, service_id, current=None):

        global streamings
        global main_servers
        global mediacatalogs

        if service_id == self.service_id:
            logging.debug("Received own announcement or already known. Ignoring")
            return
        else:
            if service.ice_isA("::IceFlix::MediaCatalog") and service_id not in mediacatalogs:
                    mediacatalogs[service_id] = IceFlix.MediaCatalogPrx.uncheckedCast(
                        service)
                    print("[CATALOGO]: Received service announcement ::IceFlix::MediaCatalog")

            if service.ice_isA('::IceFlix::StreamProvider') and service_id not in streamings:
                # almacenar en streamings_disponibles
                    print("[CATALOGO]: El servicio anunciado tiene id {}".format(service_id))
                    streamings[service_id] = IceFlix.StreamProviderPrx.uncheckedCast(
                        service)
                    print("[CATALOGO]: Received service announcement ::IceFlix::StreamProvider")

            if service.ice_isA('::IceFlix::Main') and service_id not in main_servers:

                    main_servers[service_id] = IceFlix.MainPrx.uncheckedCast(
                        service)
                    print("[CATALOGO]: Received service announcement ::IceFlix::Main", flush=True)


if __name__ == '__main__':
    app = Server()
    sys.exit(app.main(sys.argv))
