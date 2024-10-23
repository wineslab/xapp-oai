import os


# set target gnb if specified in xapp configuration file
def set_target_gnb(config: dict) -> None:

    print(config)

    try:
        gnb_id = config['containers'][0]['target_gnb']

        if gnb_id:
            print('Setting target gNB to %s' % gnb_id)
            os.environ['GNB_ID'] = gnb_id
        else:
            print('No target gNB passed in xApp config file. Targeting all registered gNBs')

    except KeyError:
        print('Field target_gnb not found in xApp config file. Targeting all registered gNBs')
