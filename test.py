_glo = 1

class A:
    global _glo
    _glo = 2
    pass
class B:
    global _glo
    # _glo = _glo
    if _glo == 1:
        print("1")
    elif _glo == 2:
        print("2")
    elif _glo == 3:
        print("3")
    pass