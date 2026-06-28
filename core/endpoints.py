class XUIInboundEndpoints:
    INBOUNDS_LIST = "/panel/api/inbounds/list"

class XUINodeEndpoints:
    NODES_LIST = "/panel/api/nodes/list"

class XUIClientsEndpoints:
    ADD_CLIENT = "/panel/api/clients/add"
    GET_TRAFFIC = "/panel/api/clients/traffic/{email}"
    DELETE_CLIENT = "/panel/api/clients/del/{email}"
    UPDATE_CLIENT = "/panel/api/clients/update/{email}"
    RESET_TRAFFIC = "/panel/api/clients/resetTraffic/{email}"

class XUISystemEndpoints:
    pass