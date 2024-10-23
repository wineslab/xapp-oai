import enum


# config file keys
class ConfigKeys(enum.Enum):
    XAPP_NAME = 'xapp_name'
    XAPP_VERSION = 'version'


# deployment constants
class DeplConstants(enum.Enum):
    RICPLT_NAMESPACE = 'ricplt'
    XAPP_NAMESPACE = 'ricxapp'
    SERVICE_HTTP = 'SERVICE_{}_{}_HTTP_PORT'
    SERVICE_RMR = 'SERVICE_{}_{}_RMR_PORT'
    CONFIG_PATH = '/ric/v1/config'
    REGISTER_PATH = 'http://service-{}-appmgr-http.{}:8080/ric/v1/register'
    DEREGISTER_PATH = 'http://service-{}-appmgr-http.{}:8080/ric/v1/deregister'
