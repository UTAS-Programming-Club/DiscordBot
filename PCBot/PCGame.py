# Generated by Haxe 4.3.6
# coding: utf-8
import sys



class Enum:
    __slots__ = ("tag", "index", "params")

    def __init__(self,tag,index,params):
        self.tag = tag
        self.index = index
        self.params = params

    def __str__(self):
        if (self.params is None):
            return self.tag
        else:
            return self.tag + '(' + (', '.join(str(v) for v in self.params)) + ')'


class backend_HealthChangeType(Enum):
    __slots__ = ()
backend_HealthChangeType.PhysicalCombat = backend_HealthChangeType("PhysicalCombat", 0, ())
backend_HealthChangeType.MagicalCombat = backend_HealthChangeType("MagicalCombat", 1, ())
backend_HealthChangeType.Heal = backend_HealthChangeType("Heal", 2, ())


class backend_Entity:
    __slots__ = ("health", "stamina", "physicalAttack", "physicalDefence", "magicalAttack", "magicalDefence", "agility")

    def __init__(self,stats):
        self.health = stats.health
        self.stamina = stats.stamina
        self.physicalAttack = stats.physicalAttack
        self.physicalDefence = stats.physicalDefence
        self.magicalAttack = stats.magicalAttack
        self.magicalDefence = stats.magicalDefence
        self.agility = stats.agility



class backend_EntityStats:
    __slots__ = ("health", "stamina", "physicalAttack", "physicalDefence", "magicalAttack", "magicalDefence", "agility")

    def __init__(self,health,stamina,physicalAttack,physicalDefence,magicalAttack,magicalDefence,agility):
        self.health = health
        self.stamina = stamina
        self.physicalAttack = physicalAttack
        self.physicalDefence = physicalDefence
        self.magicalAttack = magicalAttack
        self.magicalDefence = magicalDefence
        self.agility = agility



class backend_GameState:
    __slots__ = ("currentScreen",)

    def __init__(self):
        self.currentScreen = backend_GlobalData.mainMenu

    def HandleGameInput(self,action):
        screen = action.params[0]
        self.currentScreen = screen
        return True


class backend_ScreenActionType(Enum):
    __slots__ = ()

    @staticmethod
    def GotoScreen(screen):
        return backend_ScreenActionType("GotoScreen", 0, (screen,))


class backend_Screen:
    __slots__ = ("body",)

    def __init__(self,body):
        self.body = body



class backend_ActionScreen(backend_Screen):
    __slots__ = ("actions",)

    def __init__(self,body,actions):
        self.actions = None
        super().__init__(body)
        self.actions = actions

    def GetActions(self,state):
        _g = []
        _g1 = 0
        _g2 = self.actions
        while (_g1 < len(_g2)):
            action = (_g2[_g1] if _g1 >= 0 and _g1 < len(_g2) else None)
            _g1 = (_g1 + 1)
            if action.isVisible(state):
                _g.append(action)
        return _g



class backend_ScreenAction:
    __slots__ = ("title", "type", "isVisible")

    def __init__(self,title,_hx_type,isVisible):
        self.title = title
        self.type = _hx_type
        self.isVisible = isVisible



class backend_GlobalData:
    __slots__ = ()


class frontends_PythonFrontend:
    __slots__ = ()

    @staticmethod
    def main():
        print("This function should not be called!")


class haxe_IMap:
    __slots__ = ()


class haxe_ds_StringMap:
    __slots__ = ("h",)

    def __init__(self):
        self.h = dict()



class haxe_iterators_ArrayIterator:
    __slots__ = ("array", "current")

    def __init__(self,array):
        self.current = 0
        self.array = array

    def hasNext(self):
        return (self.current < len(self.array))

    def next(self):
        def _hx_local_3():
            def _hx_local_2():
                _hx_local_0 = self
                _hx_local_1 = _hx_local_0.current
                _hx_local_0.current = (_hx_local_1 + 1)
                return _hx_local_1
            return python_internal_ArrayImpl._get(self.array, _hx_local_2())
        return _hx_local_3()



class python_internal_ArrayImpl:
    __slots__ = ()

    @staticmethod
    def _get(x,idx):
        if ((idx > -1) and ((idx < len(x)))):
            return x[idx]
        else:
            return None


class HxOverrides:
    __slots__ = ()

    @staticmethod
    def stringOrNull(s):
        if (s is None):
            return "null"
        else:
            return s


class python_internal_MethodClosure:
    __slots__ = ("obj", "func")

    def __init__(self,obj,func):
        self.obj = obj
        self.func = func

    def __call__(self,*args):
        return self.func(self.obj,*args)



backend_Entity.MaximumStat = 100
backend_GlobalData.test = backend_ActionScreen("This is a test",[])
def _hx_init_backend_GlobalData_mainMenu():
    def _hx_local_0(state):
        return True
    return backend_ActionScreen(((("Untitled text adventure game\n" + "----------------------------\n") + "By the UTAS Programming Club\n\n") + "Currently unimplemented :("),[backend_ScreenAction("Start Game",backend_ScreenActionType.GotoScreen(backend_GlobalData.test),_hx_local_0)])
backend_GlobalData.mainMenu = _hx_init_backend_GlobalData_mainMenu()
def _hx_init_backend_GlobalData_enemyStats():
    def _hx_local_0():
        _g = haxe_ds_StringMap()
        value = backend_EntityStats(100,100,10,10,10,10,10)
        _g.h["Demon"] = value
        return _g
    return _hx_local_0()
backend_GlobalData.enemyStats = _hx_init_backend_GlobalData_enemyStats()

frontends_PythonFrontend.main()
