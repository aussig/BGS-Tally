def get_by_path(dic:dict, keys:list, default:any = None):
    """
    Access a nested dict by key sequence
    """
    try:
        for key in keys:
            dic = dic[key]
    except KeyError:
        return default

    return dic
