import constants as cst
import json
import os
import requests
import time


def register_xapp(config: dict) -> None:
        """
            function to register the xApp
        """
        retries = 5
        while retries > 0:
            time.sleep(2)
            retries -= 1
            
            # # TODO: checking for rmr/sdl/xapp health
            # healthy = self.healthcheck()
            # if not healthy:
            #     self.logger.warning(
            #         "Application='{}' is not ready yet, waiting ...".format(self._config_data.get("name")))
            #     continue

            print('Application=%s is now up and ready, continue with registration...' % config[cst.ConfigKeys.XAPP_NAME.value])
            if register(config):
                print('Registration completed, proceeding with startup...')
                break

        if retries == 0:
            print('Registration failed')


def register(config: dict) -> bool:
        """
            function to register the xApp

        Returns
        -------
        bool
            whether or not the xapp is registered
        """

        hostname = os.environ.get('HOSTNAME', None)
        if hostname is None:
            hostname = config[cst.ConfigKeys.XAPP_NAME.value]

        xappname = config[cst.ConfigKeys.XAPP_NAME.value]
        xappversion = config[cst.ConfigKeys.XAPP_VERSION.value]
        pltnamespace = cst.DeplConstants.RICPLT_NAMESPACE.value

        print('Config details hostname : %s xappname: %s xappversion : %s pltnamespace : %s' % (hostname, xappname, xappversion, pltnamespace))

        http_endpoint = get_service(hostname, cst.DeplConstants.SERVICE_HTTP.value)
        rmr_endpoint = get_service(hostname, cst.DeplConstants.SERVICE_RMR.value)
        if not http_endpoint or not rmr_endpoint:
            print('Could not resolve service endpoints: http_endpoint= %s, rmr_endpoint= %s' % (http_endpoint, rmr_endpoint))
            return False

        print('Config details hostname : %s, xappname: %s, xappversion : %s, pltnamespace : %s, http_endpoint : %s, rmr_endpoint: %s,' \
            % (hostname, xappname, xappversion, pltnamespace, http_endpoint, rmr_endpoint))

        request_string = {
            'appName': hostname,
            'appVersion': xappversion,
            'configPath': '',
            'appInstanceName': xappname,
            'httpEndpoint': http_endpoint,
            'rmrEndpoint': rmr_endpoint,
            'config': json.dumps(config)
        }

        print('REQUEST STRING:\n%s' % request_string)
        return do_post(pltnamespace, cst.DeplConstants.REGISTER_PATH.value, request_string)


def get_service(host, service) -> str:
        """
        To find the url for connecting to the service

        Parameters
        ----------
        host: string
            defines the hostname in the url
        service: string
            defines the servicename in the url

        Returns
        -------
        string
            url for the service
        """
        app_namespace = cst.DeplConstants.XAPP_NAMESPACE.value
        print('service : %s, host : %s, appnamespace : %s' % (service, host, app_namespace))
        
        svc = service.format(app_namespace.upper(), host.upper())
        urlkey = svc.replace('-', '_')
        url = os.environ.get(urlkey).split('//')
        print('Service urlkey: %s, and url: %s' % (urlkey, url))

        if len(url) > 1:
            return url[1]
        return ''


def do_post(plt_namespace, url, msg) -> bool:
        """
        registration of the xapp using the url and json msg

        Parameters
        ----------
        plt_namespace: string
            platform namespace where the xapp is running
        url: string
            url for xapp registration
        msg: string
            json msg containing the xapp details

        Returns
        -------
        bool
            whether or not the xapp is registered
        """
        if url is None:
            print('URL is empty')
            return False
        if plt_namespace is None:
            print('plt_namespace is empty')
            return False
        try:
            request_url = url.format(plt_namespace, plt_namespace)
            resp = requests.post(request_url, json=msg)
            print('Post to %s done, status: %s' % (request_url, resp.status_code))
            print('Response Text: %s' % (resp.text))
            return resp.status_code == 200 or resp.status_code == 201
        except requests.exceptions.RequestException as e:
            print('ERROR: %s' % e)
            return format(e)
        except requests.exceptions.HTTPError as e:
            print('HTTP ERROR: %s' % e)
            return e
        except requests.exceptions.ConnectionError as e:
            print('ERROR Connecting: %s' % e)
            return e
        except requests.exceptions.Timeout as e:
            print('Timeout ERROR: %s' % e)
            return e
