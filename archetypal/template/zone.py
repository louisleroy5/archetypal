################################################################################
# Module: archetypal.template
# Description:
# License: MIT, see full license in LICENSE.txt
# Web: https://github.com/samuelduchesne/archetypal
################################################################################

import collections
import functools
import logging as lg
import math
import random
import time

import matplotlib.collections
import matplotlib.colors
import networkx
import numpy as np
from eppy.bunch_subclass import BadEPFieldError
from geomeppy.geom.polygons import Polygon3D

from archetypal import log, save_and_show, timeit, settings
from archetypal.template import (
    Unique,
    UmiBase,
    ZoneConditioning,
    ZoneLoad,
    VentilationSetting,
    DomesticHotWaterSetting,
    OpaqueConstruction,
    WindowSetting,
    CREATED_OBJECTS)


class Zone(UmiBase):
    """Class containing HVAC settings: Conditioning, Domestic Hot Water, Loads,
    Ventilation, adn Consructions

    .. image:: ../images/template/zoneinfo-zone.png
    """

    _cache = {}

    def __init__(
        self,
        Conditioning=None,
        Constructions=None,
        DomesticHotWater=None,
        Loads=None,
        Ventilation=None,
        Windows=None,
        InternalMassConstruction=None,
        InternalMassExposedPerFloorArea=1.05,
        DaylightMeshResolution=1,
        DaylightWorkplaneHeight=0.8,
        **kwargs
    ):
        """Initialize :class:`Zone` object.

        Args:
            Conditioning (ZoneConditioning): Conditioning of the zone defined
                with heating/cooling and mechanical ventilation parameters (see
                :class:`ZoneConditioning`)
            Constructions (ZoneConstructionSet):
            DomesticHotWater (archetypal.template.dhw.DomesticHotWaterSetting):
            Loads (ZoneLoad): Loads of the zone defined with the lights,
                equipment and occupancy parameters (see :class:`ZoneLoad`)
            Ventilation (VentilationSetting): Ventilation settings of the zone
                defined with the infiltration rate and natural ventilation
                parameters (see :class:`VentilationSetting`)
            Windows (WindowSetting): The WindowSetting object associated with
                this zone.
            InternalMassConstruction (archetypal.OpaqueConstruction):
            InternalMassExposedPerFloorArea:
            DaylightMeshResolution (float):
            DaylightWorkplaneHeight (float):
            **kwargs:
        """
        super(Zone, self).__init__(**kwargs)

        self.Ventilation = Ventilation
        self.Loads = Loads
        self.Conditioning = Conditioning
        self.Constructions = Constructions
        self.DaylightMeshResolution = DaylightMeshResolution
        self.DaylightWorkplaneHeight = DaylightWorkplaneHeight
        self.DomesticHotWater = DomesticHotWater
        self.InternalMassConstruction = InternalMassConstruction
        self.InternalMassExposedPerFloorArea = InternalMassExposedPerFloorArea

        self.Windows = Windows  # This is not used in to_json()

        self._epbunch = kwargs.get("epbunch", None)
        self._zonesurfaces = kwargs.get("zonesurfaces", None)
        self._area = kwargs.get("area", None)
        self._volume = kwargs.get("volume", None)

        self._cache[hash(self)] = self
        CREATED_OBJECTS[hash(self)] = self

    def __add__(self, other):
        """
        Args:
            other (Zone):
        """
        # create the new merged zone from self
        return self.combine(other)

    def __hash__(self):
        return hash((self.Name, id(self.idf)))

    def __eq__(self, other):
        if not isinstance(other, Zone):
            return False
        else:
            return all(
                [
                    self.Conditioning == other.Conditioning,
                    self.Constructions == other.Constructions,
                    self.DomesticHotWater == other.DomesticHotWater,
                    self.Loads == other.Loads,
                    self.Ventilation == other.Ventilation,
                    self.Windows == other.Windows,
                    self.InternalMassConstruction == other.InternalMassConstruction,
                    self.InternalMassExposedPerFloorArea
                    == other.InternalMassExposedPerFloorArea,
                    self.DaylightMeshResolution == other.DaylightMeshResolution,
                    self.DaylightWorkplaneHeight == other.DaylightWorkplaneHeight,
                ]
            )

    @property
    def area(self):
        """Calculates the floor surface area of the zone

        Returns (float): zone's area in m²
        """
        if self._area is None:
            zone_surfs = [
                surf
                for surf in self._epbunch.zonesurfaces
                if surf.key.lower() != "internalmass"
            ]
            floors = [s for s in zone_surfs if s.Surface_Type.upper() == "FLOOR"]
            area = sum([floor.area for floor in floors])
            return area
        else:
            return self._area

    @property
    def volume(self):
        """Calculates the volume of the zone

        Returns (float): zone's volume in m³
        """
        if not self._volume:
            zone_surfs = [
                surf
                for surf in self._epbunch.zonesurfaces
                if surf.key.lower() != "internalmass"
            ]

            vol = self.get_volume_from_surfs(zone_surfs)

            if self._epbunch.Multiplier == "":
                multiplier = 1
            else:
                multiplier = float(self._epbunch.Multiplier)
            # multiply to volume by the zone multiplier.
            return vol * multiplier
        else:
            return self._volume

    @property
    def zonesurfaces(self):
        if self._zonesurfaces is None:
            return self._epbunch.zonesurfaces
        else:
            return self._zonesurfaces

    @property
    def is_core(self):
        # if all surfaces don't have boundary condition == "Outdoors"
        iscore = True
        for s in self.zonesurfaces:
            try:
                if math.isclose(int(s.tilt), 90):
                    obc = s.Outside_Boundary_Condition.lower()
                    if obc == "outdoors":
                        iscore = False
                        break
            except BadEPFieldError:
                pass  # pass surfaces that don't have an OBC,
                # eg. InternalMass
        return iscore

    @staticmethod
    def get_volume_from_surfs(zone_surfs):
        """Calculate the volume of a zone only and only if the surfaces are such
        that you can find a point inside so that you can connect every vertex to
        the point without crossing a face.

        Adapted from: https://stackoverflow.com/a/19125446

        Args:
            zone_surfs (list): List of zone surfaces (EpBunch)
        """
        vol = 0
        for surf in zone_surfs:
            polygon_d = Polygon3D(surf.coords)  # create Polygon3D from surf
            n = len(polygon_d.vertices_list)
            v2 = polygon_d[0]
            x2 = v2.x
            y2 = v2.y
            z2 = v2.z

            for i in range(1, n - 1):
                v0 = polygon_d[i]
                x0 = v0.x
                y0 = v0.y
                z0 = v0.z
                v1 = polygon_d[i + 1]
                x1 = v1.x
                y1 = v1.y
                z1 = v1.z
                # Add volume of tetrahedron formed by triangle and origin
                vol += math.fabs(
                    x0 * y1 * z2
                    + x1 * y2 * z0
                    + x2 * y0 * z1
                    - x0 * y2 * z1
                    - x1 * y0 * z2
                    - x2 * y1 * z0
                )
        return vol / 6.0

    def _conditioning(self):
        """run _conditioning and return id"""
        self.Conditioning = ZoneConditioning.from_idf(Name=random.randint(1, 999999))

    @timeit
    def _internalmassconstruction(self):
        """Group internal walls into a ThermalMass object for this Zone"""

        oc = []
        for surface in self._zonesurfaces:
            # for surf_type in self.idf.idd_index['ref2names'][
            # 'AllHeatTranSurfNames']:
            if surface.key.upper() == "INTERNALMASS":
                oc.append(OpaqueConstruction.from_epbunch(surface))
                self.InternalMassExposedPerFloorArea = (
                    float(surface.Surface_Area) / self.area
                )
        if not oc:
            # Todo: Create Equivalent InternalMassConstruction from
            #  partitions. For now, creating dummy InternalMass

            #   InternalMass,
            #     PerimInternalMass,       !- Name
            #     B_Ret_Thm_0,             !- Construction Name
            #     Perim,                   !- Zone Name
            #     2.05864785735637;        !- Surface Area {m2}

            existgin_cons = self.idf.idfobjects["CONSTRUCTION"][0]
            new = self.idf.copyidfobject(existgin_cons)
            internal_mass = "{}_InternalMass".format(self.Name)
            new.Name = internal_mass + "_construction"
            new_epbunch = self.idf.add_object(
                ep_object="InternalMass".upper(),
                save=False,
                Name=internal_mass,
                Construction_Name=new.Name,
                Zone_Name=self.Name,
                Surface_Area=0,
            )

            oc.append(OpaqueConstruction.from_epbunch(new_epbunch, idf=self.idf))
            self.InternalMassExposedPerFloorArea = 0

        if self.InternalMassExposedPerFloorArea is None:
            self.InternalMassExposedPerFloorArea = 0

        from operator import add

        return functools.reduce(add, oc)

    def _loads(self):
        """run loads and return id"""
        self.Loads = ZoneLoad(Name=str(random.randint(1, 999999)))

    def _ventilation(self):
        self.Ventilation = VentilationSetting(Name=str(random.randint(1, 999999)))

    def _constructions(self):
        """run construction sets and return id"""
        set_name = "_".join([self.Name, "constructions"])
        self.Constructions = ZoneConstructionSet.from_idf(
            Zone_Names=self.Zone_Names, sql=self.sql, Name=set_name, idf=self.idf
        )

    def _domestichotwater(self):
        """run domestic hot water and return id"""
        self.DomesticHotWater = DomesticHotWaterSetting(
            Name=str(random.randint(1, 999999))
        )

    def to_json(self):
        data_dict = collections.OrderedDict()

        data_dict["$id"] = str(self.id)
        data_dict["Conditioning"] = self.Conditioning.to_dict()
        data_dict["Constructions"] = self.Constructions.to_dict()
        data_dict["DaylightMeshResolution"] = self.DaylightMeshResolution
        data_dict["DaylightWorkplaneHeight"] = self.DaylightWorkplaneHeight
        data_dict["DomesticHotWater"] = self.DomesticHotWater.to_dict()
        data_dict["InternalMassConstruction"] = self.InternalMassConstruction.to_dict()
        data_dict[
            "InternalMassExposedPerFloorArea"
        ] = self.InternalMassExposedPerFloorArea
        data_dict["Loads"] = self.Loads.to_dict()
        data_dict["Ventilation"] = self.Ventilation.to_dict()
        data_dict["Category"] = self.Category
        data_dict["Comments"] = self.Comments
        data_dict["DataSource"] = self.DataSource
        data_dict["Name"] = self.Name

        return data_dict

    @classmethod
    def from_json(cls, *args, **kwargs):
        """
        Args:
            *args:
            **kwargs:
        """
        zone = cls(*args, **kwargs)

        ref = kwargs.get("Conditioning", None)
        zone.Conditioning = zone.get_ref(ref)
        ref = kwargs.get("Constructions", None)
        zone.Constructions = zone.get_ref(ref)
        ref = kwargs.get("DomesticHotWater", None)
        zone.DomesticHotWater = zone.get_ref(ref)
        ref = kwargs.get("InternalMassConstruction", None)
        zone.InternalMassConstruction = zone.get_ref(ref)
        ref = kwargs.get("Loads", None)
        zone.Loads = zone.get_ref(ref)
        ref = kwargs.get("Ventilation", None)
        zone.Ventilation = zone.get_ref(ref)

        return zone

    @classmethod
    def from_zone_epbunch(cls, zone_ep, sql):
        """Create a Zone object from an eppy 'ZONE' epbunch.

        Args:
            zone_ep (EpBunch): The Zone EpBunch.
            sql (dict): The sql dict for this IDF object.
        """
        cached = cls.get_cached(zone_ep.Name, zone_ep.theidf)
        if cached:
            return cached
        start_time = time.time()
        log('\nConstructing :class:`Zone` for zone "{}"'.format(zone_ep.Name))
        name = zone_ep.Name
        zone = cls(
            Name=name,
            idf=zone_ep.theidf,
            sql=sql,
            Category=zone_ep.theidf.building_name(use_idfname=True),
        )

        zone._epbunch = zone_ep
        zone._zonesurfaces = zone_ep.zonesurfaces

        zone.Constructions = ZoneConstructionSet.from_zone(zone)
        zone.Conditioning = ZoneConditioning.from_zone(zone)
        zone.Ventilation = VentilationSetting.from_zone(zone)
        zone.DomesticHotWater = DomesticHotWaterSetting.from_zone(zone)
        zone.Loads = ZoneLoad.from_zone(zone)
        zone.InternalMassConstruction = zone._internalmassconstruction()
        zone.Windows = WindowSetting.from_zone(zone)

        log(
            'completed Zone "{}" constructor in {:,.2f} seconds'.format(
                zone_ep.Name, time.time() - start_time
            )
        )
        return zone

    @classmethod
    def get_cached(cls, name, idf):
        """Retrieve the cached object by Name and idf name. If not, returns
        None.

        Args:
            name (str): The name of the object in the cache.
            idf (IDF): The :class:`IDF` object.
        """
        try:
            cached = cls._cache[hash((name, id(idf)))]
        except KeyError:
            return None
        else:
            return cached

    def combine(self, other, weights=None):
        """
        Args:
            other (Zone):
            weights (list-like, optional): A list-like object of len 2. If None,
                the volume of the zones for which self and other belongs is
                used.

        Returns:
            (Zone): the combined Zone object.
        """
        # Check if other is the same type as self
        if not isinstance(other, self.__class__):
            msg = "Cannot combine %s with %s" % (
                self.__class__.__name__,
                other.__class__.__name__,
            )
            raise NotImplementedError(msg)

        # Check if other is not the same as self
        if self == other:
            return self

        incoming_zone_data = self.__dict__.copy()
        incoming_zone_data.pop("Name")

        meta = self._get_predecessors_meta(other)

        if not weights:
            zone_weight = settings.zone_weight
            weights = [
                getattr(self, str(zone_weight)),
                getattr(other, str(zone_weight)),
            ]
            log(
                'using zone {} "{}" as weighting factor in "{}" '
                "combine.".format(
                    zone_weight,
                    " & ".join(list(map(str, map(int, weights)))),
                    self.__class__.__name__,
                )
            )

        attr = dict(
            Conditioning=self.Conditioning.combine(other.Conditioning, weights),
            Constructions=self.Constructions.combine(other.Constructions, weights),
            Ventilation=self.Ventilation.combine(other.Ventilation, weights),
            Windows=None
            if self.Windows is None or other.Windows is None
            else self.Windows.combine(other.Windows, weights),
            DaylightMeshResolution=self._float_mean(
                other, "DaylightMeshResolution", weights=weights
            ),
            DaylightWorkplaneHeight=self._float_mean(
                other, "DaylightWorkplaneHeight", weights
            ),
            DomesticHotWater=self.DomesticHotWater.combine(
                other.DomesticHotWater, weights
            ),
            InternalMassConstruction=self.InternalMassConstruction.combine(
                other.InternalMassConstruction, weights
            ),
            InternalMassExposedPerFloorArea=self._float_mean(
                other, "InternalMassExposedPerFloorArea", weights
            ),
            Loads=self.Loads.combine(other.Loads, weights),
        )
        new_obj = self.__class__(**meta, **attr)
        new_obj._volume = self.volume + other.volume
        new_obj._area = self.area + other.area
        attr["Conditioning"]._belongs_to_zone = new_obj
        attr["Constructions"]._belongs_to_zone = new_obj
        attr["Ventilation"]._belongs_to_zone = new_obj
        attr["DomesticHotWater"]._belongs_to_zone = new_obj
        if attr["Windows"]:
            attr["Windows"]._belongs_to_zone = new_obj
        new_obj._predecessors.extend(self.predecessors + other.predecessors)
        return new_obj


def resolve_obco(this):
    """Resolve the outside boundary condition of a surface and return the other
    SURFACE epbunch and, if possible, the ZONE epbunch.

    Args:
        this (EpBunch): The surface for which we are identifying the boundary
            object.

    Returns:
        (EpBunch, EpBunch): A tuple of:

            EpBunch: The other surface EpBunch: The other zone

    Notes:
        Info on the Outside Boundary Condition Object of a surface of type
        BuildingSurface:Detailed:

        Non-blank only if the field `Outside Boundary Condition` is *Surface*,
        *Zone*, *OtherSideCoefficients* or *OtherSideConditionsModel*. If
        Surface, specify name of corresponding surface in adjacent zone or
        specify current surface name for internal partition separating like
        zones. If Zone, specify the name of the corresponding zone and the
        program will generate the corresponding interzone surface. If
        Foundation, specify the name of the corresponding Foundation object and
        the program will calculate the heat transfer appropriately. If
        OtherSideCoefficients, specify name of
        SurfaceProperty:OtherSideCoefficients. If OtherSideConditionsModel,
        specify name of SurfaceProperty:OtherSideConditionsModel.
    """

    # other belongs to which zone?
    # for key in this.getfieldidd_item('Outside_Boundary_Condition_Object',
    #                                  'validobjects'):

    obc = this.Outside_Boundary_Condition

    if obc.upper() == "ZONE":
        name = this.Outside_Boundary_Condition_Object
        adj_zone = this.theidf.getobject("ZONE", name)
        return None, adj_zone

    elif obc.upper() == "SURFACE":
        obco = this.get_referenced_object("Outside_Boundary_Condition_Object")
        adj_zone = obco.theidf.getobject("ZONE", obco.Zone_Name)
        return obco, adj_zone
    else:
        return None, None


def surface_dispatcher(surf, zone):
    """
    Args:
        surf (EpBunch):
        zone (EpBunch):
    """
    dispatch = {
        ("Wall", "Outdoors"): ZoneConstructionSet._do_facade,
        ("Floor", "Ground"): ZoneConstructionSet._do_ground,
        ("Floor", "Outdoors"): ZoneConstructionSet._do_ground,
        ("Floor", "Foundation"): ZoneConstructionSet._do_ground,
        ("Floor", "Surface"): ZoneConstructionSet._do_slab,
        ("Floor", "Adiabatic"): ZoneConstructionSet._do_slab,
        ("Floor", "Zone"): ZoneConstructionSet._do_slab,
        ("Wall", "Adiabatic"): ZoneConstructionSet._do_partition,
        ("Wall", "Surface"): ZoneConstructionSet._do_partition,
        ("Wall", "Zone"): ZoneConstructionSet._do_partition,
        ("Wall", "Ground"): ZoneConstructionSet._do_basement,
        ("Roof", "Outdoors"): ZoneConstructionSet._do_roof,
        ("Roof", "Zone"): ZoneConstructionSet._do_roof,
        ("Roof", "Surface"): ZoneConstructionSet._do_roof,
        ("Ceiling", "Adiabatic"): ZoneConstructionSet._do_slab,
        ("Ceiling", "Surface"): ZoneConstructionSet._do_slab,
        ("Ceiling", "Zone"): ZoneConstructionSet._do_slab,
    }
    if surf.key.upper() != "INTERNALMASS":
        a, b = surf["Surface_Type"].capitalize(), surf["Outside_Boundary_Condition"]
        try:
            yield dispatch[a, b](surf)
        except KeyError as e:
            raise NotImplementedError(
                "surface '%s' in zone '%s' not supported by surface dispatcher "
                "with keys %s" % (surf.Name, zone.Name, e)
            )


def label_surface(row):
    """Takes a boundary and returns its corresponding umi-Category

    Args:
        row:
    """
    # Floors
    if row["Surface_Type"] == "Floor":
        if row["Outside_Boundary_Condition"] == "Surface":
            return "Interior Floor"
        if row["Outside_Boundary_Condition"] == "Ground":
            return "Ground Floor"
        if row["Outside_Boundary_Condition"] == "Outdoors":
            return "Exterior Floor"
        if row["Outside_Boundary_Condition"] == "Adiabatic":
            return "Interior Floor"
        else:
            return "Other"

    # Roofs & Ceilings
    if row["Surface_Type"] == "Roof":
        return "Roof"
    if row["Surface_Type"] == "Ceiling":
        return "Interior Floor"
    # Walls
    if row["Surface_Type"] == "Wall":
        if row["Outside_Boundary_Condition"] == "Surface":
            return "Partition"
        if row["Outside_Boundary_Condition"] == "Outdoors":
            return "Facade"
        if row["Outside_Boundary_Condition"] == "Adiabatic":
            return "Partition"
    return "Other"


def type_surface(row):
    """Takes a boundary and returns its corresponding umi-type

    Args:
        row:
    """

    # Floors
    if row["Surface_Type"] == "Floor":
        if row["Outside_Boundary_Condition"] == "Surface":
            return 3  # umi defined
        if row["Outside_Boundary_Condition"] == "Ground":
            return 2  # umi defined
        if row["Outside_Boundary_Condition"] == "Outdoors":
            return 4  # umi defined
        if row["Outside_Boundary_Condition"] == "Adiabatic":
            return 5
        else:
            return ValueError('Cannot find Construction Type for "{}"'.format(row))

    # Roofs & Ceilings
    elif row["Surface_Type"] == "Roof":
        return 1
    elif row["Surface_Type"] == "Ceiling":
        return 3
    # Walls
    elif row["Surface_Type"] == "Wall":
        if row["Outside_Boundary_Condition"] == "Surface":
            return 5  # umi defined
        if row["Outside_Boundary_Condition"] == "Outdoors":
            return 0  # umi defined
        if row["Outside_Boundary_Condition"] == "Adiabatic":
            return 5  # umi defined
    else:
        raise ValueError('Cannot find Construction Type for "{}"'.format(row))


def zone_information(df):
    """Each zone_loads is summarized in a simple set of statements

    Args:
        df:

    Returns:
        df

    References:
        * ` Zone Loads Information

        < https://bigladdersoftware.com/epx/docs/8-3/output-details-and
        -examples/eplusout.eio.html#zone_loads-information>`_
    """
    df = get_from_tabulardata(df)
    tbstr = df[
        (df.ReportName == "Initialization Summary")
        & (df.TableName == "Zone Information")
    ].reset_index()
    # Ignore Zone that are not part of building area
    pivoted = tbstr.pivot_table(
        index=["RowName"],
        columns="ColumnName",
        values="Value",
        aggfunc=lambda x: " ".join(x),
    )

    return pivoted.loc[pivoted["Part of Total Building Area"] == "Yes", :]


def get_from_tabulardata(sql):
    """Returns a DataFrame from the 'TabularDataWithStrings' table.

    Args:
        sql (dict):

    Returns:
        (pandas.DataFrame)
    """
    tab_data_wstring = sql["TabularDataWithStrings"]
    tab_data_wstring.index.names = ["Index"]

    # strip whitespaces
    tab_data_wstring.Value = tab_data_wstring.Value.str.strip()
    tab_data_wstring.RowName = tab_data_wstring.RowName.str.strip()
    return tab_data_wstring


def iscore(row):
    """Helps to group by core and perimeter zones. If any of "has `core` in
    name" and "ExtGrossWallArea == 0" is true, will consider zone_loads as core,
    else as perimeter.

    Todo:
        * assumes a basement zone_loads will be considered as a core zone_loads
          since no ext wall area for basements.

    Args:
        row (pandas.Series): a row

    Returns:
        str: 'Core' or 'Perimeter'
    """
    if any(
        [
            "core" in row["Zone Name"].lower(),
            float(row["Exterior Gross Wall Area {m2}"]) == 0,
        ]
    ):
        # We look for the string `core` in the Zone_Name
        return "Core"
    elif row["Part of Total Building Area"] == "No":
        return np.NaN
    elif "plenum" in row["Zone Name"].lower():
        return np.NaN
    else:
        return "Perimeter"


class ZoneConstructionSet(UmiBase, metaclass=Unique):
    """Zone-specific :class:`Construction` ids"""

    def __init__(
        self,
        *args,
        Zone_Names=None,
        Slab=None,
        IsSlabAdiabatic=False,
        Roof=None,
        IsRoofAdiabatic=False,
        Partition=None,
        IsPartitionAdiabatic=False,
        Ground=None,
        IsGroundAdiabatic=False,
        Facade=None,
        IsFacadeAdiabatic=False,
        **kwargs
    ):
        """
        Args:
            *args:
            Zone_Names:
            Slab (OpaqueConstruction):
            IsSlabAdiabatic (bool):
            Roof (OpaqueConstruction):
            IsRoofAdiabatic (bool):
            Partition (OpaqueConstruction):
            IsPartitionAdiabatic (bool):
            Ground (OpaqueConstruction):
            IsGroundAdiabatic (bool):
            Facade (OpaqueConstruction):
            IsFacadeAdiabatic (bool):
            **kwargs:
        """
        super(ZoneConstructionSet, self).__init__(*args, **kwargs)
        self.Slab = Slab
        self.IsSlabAdiabatic = IsSlabAdiabatic
        self.Roof = Roof
        self.IsRoofAdiabatic = IsRoofAdiabatic
        self.Partition = Partition
        self.IsPartitionAdiabatic = IsPartitionAdiabatic
        self.Ground = Ground
        self.IsGroundAdiabatic = IsGroundAdiabatic
        self.Facade = Facade
        self.IsFacadeAdiabatic = IsFacadeAdiabatic

        self.Zone_Names = Zone_Names
        self._belongs_to_zone = kwargs.get("zone", None)

    def __add__(self, other):
        """Overload + to implement self.combine.

        Args:
            other:
        """
        return self.combine(other)

    def __hash__(self):
        return hash((self.__class__.__name__, self.Name))

    def __eq__(self, other):
        if not isinstance(other, ZoneConstructionSet):
            return False
        else:
            return all(
                [
                    self.Zone_Names == other.Zone_Names,
                    self.Slab == other.Slab,
                    self.IsSlabAdiabatic == other.IsSlabAdiabatic,
                    self.Roof == other.Roof,
                    self.IsRoofAdiabatic == other.IsRoofAdiabatic,
                    self.Partition == other.Partition,
                    self.IsPartitionAdiabatic == other.IsPartitionAdiabatic,
                    self.Ground == other.Ground,
                    self.IsGroundAdiabatic == other.IsGroundAdiabatic,
                    self.Facade == other.Facade,
                    self.IsFacadeAdiabatic == other.IsFacadeAdiabatic,
                ]
            )

    def combine(self, other, weights=None):
        """Append other to self. Return self + other as a new object.

        Args:
            other (ZoneConstructionSet):
            weights:

        Returns:
            (ZoneConstructionSet): the combined ZoneConstructionSet object.
        """
        # Check if other is the same type as self
        if not isinstance(other, self.__class__):
            msg = "Cannot combine %s with %s" % (
                self.__class__.__name__,
                other.__class__.__name__,
            )
            raise NotImplementedError(msg)

        # Check if other is not the same as self
        if self == other:
            return self

        if not weights:
            weights = [self._belongs_to_zone.volume, other._belongs_to_zone.volume]
            log(
                'using zone volume "{}" as weighting factor in "{}" '
                "combine.".format(
                    " & ".join(list(map(str, map(int, weights)))),
                    self.__class__.__name__,
                )
            )

        meta = self._get_predecessors_meta(other)
        new_attr = dict(
            Slab=self.Slab.combine(other.Slab, weights),
            IsSlabAdiabatic=self.IsSlabAdiabatic,
            Roof=self.Roof + other.Roof,
            IsRoofAdiabatic=self.IsRoofAdiabatic,
            Partition=self.Partition + other.Partition,
            IsPartitionAdiabatic=self.IsPartitionAdiabatic,
            Ground=self.Ground + other.Ground,
            IsGroundAdiabatic=self.IsGroundAdiabatic,
            Facade=self.Facade + other.Facade,
            IsFacadeAdiabatic=self.IsFacadeAdiabatic,
        )
        new_obj = self.__class__(**meta, **new_attr)
        new_obj._predecessors.extend(self.predecessors + other.predecessors)
        return new_obj

    @classmethod
    def from_json(cls, *args, **kwargs):
        """
        Args:
            *args:
            **kwargs:
        """
        zc = cls(*args, **kwargs)

        ref = kwargs.get("Facade", None)
        zc.Facade = zc.get_ref(ref)

        ref = kwargs.get("Ground", None)
        zc.Ground = zc.get_ref(ref)

        ref = kwargs.get("Partition", None)
        zc.Partition = zc.get_ref(ref)

        ref = kwargs.get("Roof", None)
        zc.Roof = zc.get_ref(ref)

        ref = kwargs.get("Slab", None)
        zc.Slab = zc.get_ref(ref)

        return zc

    def to_json(self):
        """Convert class properties to dict"""
        data_dict = collections.OrderedDict()

        data_dict["$id"] = str(self.id)
        data_dict["Facade"] = {"$ref": str(self.Facade.id)}
        data_dict["Ground"] = {"$ref": str(self.Ground.id)}
        data_dict["Partition"] = {"$ref": str(self.Partition.id)}
        data_dict["Roof"] = {"$ref": str(self.Roof.id)}
        data_dict["Slab"] = {"$ref": str(self.Slab.id)}
        data_dict["IsFacadeAdiabatic"] = self.IsFacadeAdiabatic
        data_dict["IsGroundAdiabatic"] = self.IsGroundAdiabatic
        data_dict["IsPartitionAdiabatic"] = self.IsPartitionAdiabatic
        data_dict["IsRoofAdiabatic"] = self.IsRoofAdiabatic
        data_dict["IsSlabAdiabatic"] = self.IsSlabAdiabatic
        data_dict["Category"] = self.Category
        data_dict["Comments"] = self.Comments
        data_dict["DataSource"] = self.DataSource
        data_dict["Name"] = self.Name

        return data_dict

    @classmethod
    @timeit
    def from_zone(cls, zone):
        """
        Args:
            zone (Zone):
        """
        name = zone.Name + "_ZoneConstructionSet"
        # dispatch surfaces
        facade, ground, partition, roof, slab = [], [], [], [], []
        zonesurfaces = zone._zonesurfaces
        for surf in zonesurfaces:
            for disp_surf in surface_dispatcher(surf, zone):

                if disp_surf.Surface_Type == "Facade":
                    facade.append(disp_surf)
                elif disp_surf.Surface_Type == "Ground":
                    ground.append(disp_surf)
                elif disp_surf.Surface_Type == "Partition":
                    partition.append(disp_surf)
                elif disp_surf.Surface_Type == "Roof":
                    roof.append(disp_surf)
                elif disp_surf.Surface_Type == "Slab":
                    slab.append(disp_surf)
                else:
                    msg = (
                        'Surface Type "{}" is not known, this method is not'
                        " implemented".format(disp_surf.Surface_Type)
                    )
                    raise NotImplementedError(msg)

        # Returning a set() for each groups of Constructions.

        facades = set(facade)
        if facades:
            facade = functools.reduce(lambda a, b: a + b, facades)
        else:
            facade = OpaqueConstruction.generic(idf=zone.idf)
        grounds = set(ground)
        if grounds:
            ground = functools.reduce(lambda a, b: a + b, grounds)
        else:
            ground = OpaqueConstruction.generic(idf=zone.idf)
        partitions = set(partition)
        if partitions:
            partition = functools.reduce(lambda a, b: a + b, partitions)
        else:
            partition = OpaqueConstruction.generic(idf=zone.idf)
        roofs = set(roof)
        if roofs:
            roof = functools.reduce(lambda a, b: a + b, roofs)
        else:
            roof = OpaqueConstruction.generic(idf=zone.idf)
        slabs = set(slab)
        if slabs:
            slab = functools.reduce(lambda a, b: a + b, slabs)
        else:
            slab = OpaqueConstruction.generic(idf=zone.idf)

        z_set = cls(
            Facade=facade,
            Ground=ground,
            Partition=partition,
            Roof=roof,
            Slab=slab,
            Name=name,
            zone=zone,
            idf=zone.idf,
            Category=zone.idf.building_name(use_idfname=True),
        )
        return z_set

    @staticmethod
    def _do_facade(surf):
        """
        Args:
            surf (EpBunch):
        """
        log(
            'surface "%s" assigned as a Facade' % surf.Name,
            lg.DEBUG,
            name=surf.theidf.name,
        )
        oc = OpaqueConstruction.from_epbunch(
            surf.theidf.getobject("Construction".upper(), surf.Construction_Name)
        )
        oc.area = surf.area
        oc.Surface_Type = "Facade"
        return oc

    @staticmethod
    def _do_ground(surf):
        """
        Args:
            surf (EpBunch):
        """
        log(
            'surface "%s" assigned as a Ground' % surf.Name,
            lg.DEBUG,
            name=surf.theidf.name,
        )
        oc = OpaqueConstruction.from_epbunch(
            surf.theidf.getobject("Construction".upper(), surf.Construction_Name)
        )
        oc.area = surf.area
        oc.Surface_Type = "Ground"
        return oc

    @staticmethod
    def _do_partition(surf):
        """
        Args:
            surf (EpBunch):
        """
        log(
            'surface "%s" assigned as a Partition' % surf.Name,
            lg.DEBUG,
            name=surf.theidf.name,
        )
        oc = OpaqueConstruction.from_epbunch(
            surf.theidf.getobject("Construction".upper(), surf.Construction_Name)
        )
        oc.area = surf.area
        oc.Surface_Type = "Partition"
        return oc

    @staticmethod
    def _do_roof(surf):
        """
        Args:
            surf (EpBunch):
        """
        log(
            'surface "%s" assigned as a Roof' % surf.Name,
            lg.DEBUG,
            name=surf.theidf.name,
        )
        oc = OpaqueConstruction.from_epbunch(
            surf.theidf.getobject("Construction".upper(), surf.Construction_Name)
        )
        oc.area = surf.area
        oc.Surface_Type = "Roof"
        return oc

    @staticmethod
    def _do_slab(surf):
        """
        Args:
            surf (EpBunch):
        """
        log(
            'surface "%s" assigned as a Slab' % surf.Name,
            lg.DEBUG,
            name=surf.theidf.name,
        )
        oc = OpaqueConstruction.from_epbunch(
            surf.theidf.getobject("Construction".upper(), surf.Construction_Name)
        )
        oc.area = surf.area
        oc.Surface_Type = "Slab"
        return oc

    @staticmethod
    def _do_basement(surf):
        """
        Args:
            surf (EpBunch):
        """
        log(
            'surface "%s" ignored because basement facades are not supported'
            % surf.Name,
            lg.WARNING,
            name=surf.theidf.name,
        )
        oc = OpaqueConstruction.from_epbunch(
            surf.theidf.getobject("Construction".upper(), surf.Construction_Name)
        )
        oc.area = surf.area
        oc.Surface_Type = "Facade"
        return oc


class ZoneGraph(networkx.Graph):
    """A subclass of :class:`networkx.Graph`. This class implements useful
    methods to visualize and navigate a template along the thermal adjacency of
    its zones.

    There are currently two methods to visualize the graph:

    - :func:`plot in 3d <plot_graph3d>` to get a 3-dimensional view of the
      building.
    - :func:`plot in 2d <plot_graph2d>` to get a 2-dimensional view of the
      building zones

    Note:
        A Graph stores nodes and edges with optional data, or attributes.

        Graphs hold undirected edges. Self loops are allowed but multiple
        (parallel) edges are not.

        Nodes can be arbitrary (hashable) Python objects with optional key/value
        attributes. By convention `None` is not used as a node.

        Edges are represented as links between nodes with optional key/value
        attributes.
    """

    def __init__(self, incoming_graph_data=None, **attr):
        """Initialize a graph with edges, name, or graph attributes.

        Wrapper around the :class:`networkx.Graph` class.

        Args:
            incoming_graph_data: input graph (optional, default: None) Data to
                initialize graph. If None (default) an empty graph is created.
                The data can be an edge list, or any NetworkX graph object. If
                the corresponding optional Python packages are installed the
                data can also be a NumPy matrix or 2d ndarray, a SciPy sparse
                matrix, or a PyGraphviz graph.
            attr: keyword arguments, optional (default= no attributes)
                Attributes to add to graph as key=value pairs.
        """
        super(ZoneGraph, self).__init__(incoming_graph_data=incoming_graph_data, **attr)

    def plot_graph3d(
        self,
        fig_height=None,
        fig_width=6,
        save=False,
        show=True,
        close=False,
        ax=None,
        axis_off=False,
        cmap="plasma",
        dpi=300,
        file_format="png",
        azim=-60,
        elev=30,
        proj_type="persp",
        filename=None,
        annotate=False,
        plt_style="ggplot",
    ):
        """Plot the :class:`archetypal.template.ZoneGraph` in a 3D plot.

        The size of the node is relative to its
        :func:`networkx.Graph.degree`. The node degree is the number of edges
        adjacent to the node.

        The nodes are positioned in 3d space according to the mean value of
        the surfaces centroids. For concave volumes, this corresponds to the
        center of gravity of the volume. Some weird positioning can occur for
        convex volumes.

        Todo:
            Create an Example

        Args:
            fig_height (float): matplotlib figure height in inches.
            fig_width (float): matplotlib figure width in inches.
            save (bool): if True, save the figure as an image file to disk.
            show (bool): if True, show the figure.
            close (bool): close the figure (only if show equals False) to
                prevent display.
            ax (matplotlib.axes._axes.Axes, optional): An existing axes object
                on which to plot this graph.
            axis_off (bool): If True, turn off the matplotlib axis.
            cmap (str): The name a registered
                :class:`matplotlib.colors.Colormap`.
            dpi (int): the resolution of the image file if saving.
            file_format (str): the format of the file to save (e.g., 'jpg',
                'png', 'svg', 'pdf')
            azim (float): Azimuthal viewing angle, defaults to -60.
            elev (float): Elevation viewing angle, defaults to 30.
            proj_type (str): Type of projection, accepts 'persp' and 'ortho'.
            filename (str): the name of the file if saving.
            annotate (bool or str or tuple): If True, annotates the node with
                the Zone Name. Pass an EpBunch *field_name* to retrieve data
                from the zone EpBunch. Pass a tuple (data, key) to retrieve data
                from the graph: eg. ('core', None) will retrieve the attribute
                'core' associated to the node. The second tuple element serves
                as a key on the first: G.nodes(data=data)[key].
            plt_style (str, dict, or list): A style specification. Valid options
                are: - str: The name of a style or a path/URL to a style file.
                For a list of available style names, see `style.available` . -
                dict: Dictionary with valid key/value pairs for
                :attr:`matplotlib.rcParams`. - list: A list of style specifiers
                (str or dict) applied from first to last in the list.

        Returns:
            fig, ax: fig, ax
        """
        from mpl_toolkits.mplot3d import Axes3D
        import matplotlib.pyplot as plt
        import numpy as np

        def avg(zone):
            """calculate the zone centroid coordinates"""
            x_, y_, z_, dem = 0, 0, 0, 0
            from geomeppy.geom.polygons import Polygon3D, Vector3D
            from geomeppy.recipes import translate_coords

            ggr = zone.theidf.idfobjects["GLOBALGEOMETRYRULES"][0]

            for surface in zone.zonesurfaces:
                if surface.key.lower() == "internalmass":
                    pass
                else:
                    dem += 1  # Counter for average calc at return
                    if ggr.Coordinate_System.lower() == "relative":
                        # add zone origin to surface coordinates and create
                        # Polygon3D from updated coords.
                        zone = zone.theidf.getobject("ZONE", surface.Zone_Name)
                        poly3d = Polygon3D(surface.coords)
                        origin = (zone.X_Origin, zone.Y_Origin, zone.Z_Origin)
                        coords = translate_coords(poly3d, Vector3D(*origin))
                        poly3d = Polygon3D(coords)
                    else:
                        # Polygon3D from surface coords
                        poly3d = Polygon3D(surface.coords)
                    x, y, z = poly3d.centroid
                    x_ += x
                    y_ += y
                    z_ += z
            return x_ / dem, y_ / dem, z_ / dem

        # Get node positions in a dictionary
        pos = {name: avg(epbunch) for name, epbunch in self.nodes(data="epbunch")}

        # Get the maximum number of edges adjacent to a single node
        edge_max = max(1, max([self.degree(i) for i in self.nodes]))  # min = 1

        # Define color range proportional to number of edges adjacent to a
        # single node
        colors = {
            i: plt.cm.get_cmap(cmap)(self.degree(i) / edge_max) for i in self.nodes
        }

        if annotate:
            # annotate can be bool or str.
            if isinstance(annotate, bool):
                # if True, default to 'Name' field
                annotate = "Name"
            if isinstance(annotate, str):
                # create dict of the form {id: (x, y, z, label, zdir)}. zdir is
                # None by default.
                labels = {
                    name: (*pos[name], data[annotate], None)
                    for name, data in self.nodes(data="epbunch")
                }
            if isinstance(annotate, tuple):
                data, key = annotate
                if key:
                    labels = {
                        name: (*pos[name], data[key], None)
                        for name, data in self.nodes(data=data)
                    }
                else:
                    labels = {
                        name: (*pos[name], data, None)
                        for name, data in self.nodes(data=data)
                    }

        # 3D network plot
        with plt.style.context((plt_style)):
            if fig_height is None:
                fig_height = fig_width

            if ax:
                fig = plt.gcf()
            else:
                fig = plt.figure(figsize=(fig_width, fig_height), dpi=dpi)
                ax = Axes3D(fig)

            # Loop on the pos dictionary to extract the x,y,z coordinates of
            # each node
            for key, value in pos.items():
                xi = value[0]
                yi = value[1]
                zi = value[2]

                # Scatter plot
                ax.scatter(
                    xi,
                    yi,
                    zi,
                    color=colors[key],
                    s=20 + 20 * self.degree(key),
                    edgecolors="k",
                    alpha=0.7,
                )
                if annotate:
                    # Add node label
                    ax.text(*labels[key], fontsize=4)
            # Loop on the list of edges to get the x,y,z, coordinates of the
            # connected nodes
            # Those two points are the extrema of the line to be plotted
            for i, j in enumerate(self.edges()):
                x = np.array((pos[j[0]][0], pos[j[1]][0]))
                y = np.array((pos[j[0]][1], pos[j[1]][1]))
                z = np.array((pos[j[0]][2], pos[j[1]][2]))

                # Plot the connecting lines
                ax.plot(x, y, z, c="black", alpha=0.5)

        # Set the initial view
        ax.view_init(elev, azim)
        ax.set_proj_type(proj_type)

        # Hide the axes
        if axis_off:
            ax.set_axis_off()

        if filename is None:
            filename = "unnamed"

        fig, ax = save_and_show(
            fig=fig,
            ax=ax,
            save=save,
            show=show,
            close=close,
            filename=filename,
            file_format=file_format,
            dpi=dpi,
            axis_off=axis_off,
            extent=None,
        )
        return fig, ax

    def plot_graph2d(
        self,
        layout_function,
        *func_args,
        color_nodes=None,
        fig_height=None,
        fig_width=6,
        node_labels_to_integers=False,
        legend=False,
        with_labels=True,
        arrows=True,
        save=False,
        show=True,
        close=False,
        ax=None,
        axis_off=False,
        cmap="plasma",
        dpi=300,
        file_format="png",
        filename="unnamed",
        plt_style="ggplot",
        extent="tight",
        **kwargs
    ):
        """Plot the adjacency of the zones as a graph. Choose a layout from the
        :mod:`networkx.drawing.layout` module, the
        :mod:`Graphviz AGraph (dot)<networkx.drawing.nx_agraph>` module, the
        :mod:`Graphviz with pydot<networkx.drawing.nx_pydot>` module. Then, plot
        the graph using matplotlib using the :mod:`networkx.drawing.py_lab`

        Examples:
            >>> G = BuildingTemplate().zone_graph
            >>> G.plot_graph2d(nx.nx_agraph.graphviz_layout, ('dot'),
            >>>                font_color='w', legend=True, font_size=8,
            >>>                color_nodes='core',
            >>>                node_labels_to_integers=True,
            >>>                plt_style='seaborn', save=True,
            >>>                filename='test')

        Args:
            layout_function (func): One of the networkx layout functions.
            *func_args: The layout function arguments as a tuple. The first
                argument (self) is already supplied.
            color_nodes (bool or str): False by default. If a string is passed
                the nodes are colored according to a data attribute of the
                graph. By default, the original node names is accessed with the
                'name' attribute.
            fig_height (float): matplotlib figure height in inches.
            fig_width (float): matplotlib figure width in inches.
            node_labels_to_integers:
            legend:
            with_labels (bool, optional): Set to True to draw labels on the
            arrows (bool, optional): If True, draw arrowheads. Note: Arrows will
                be the same color as edges.
            save (bool): if True, save the figure as an image file to disk.
            show (bool): if True, show the figure.
            close (bool): close the figure (only if show equals False) to
                prevent display.
            ax (matplotlib.axes._axes.Axes, optional): An existing axes object
                on which to plot this graph.
            axis_off (bool): If True, turn off the matplotlib axis.
            cmap (str): The name a registered
                :class:`matplotlib.colors.Colormap`.
            dpi (int): the resolution of the image file if saving.
            file_format (str): the format of the file to save (e.g., 'jpg',
                'png', 'svg', 'pdf')
            filename (str): the name of the file if saving.
            plt_style (str, dict, or list): A style specification. Valid options
                are: - str: The name of a style or a path/URL to a style file.
                For a list of available style names, see `style.available` . -
                dict: Dictionary with valid key/value pairs for
                :attr:`matplotlib.rcParams`. - list: A list of style specifiers
                (str or dict) applied from first to last in the list.
            extent:
            **kwargs: keywords passed to :func:`networkx.draw_networkx`

        Returns:
            (tuple): The fig and ax objects
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            raise ImportError("Matplotlib required for draw()")
        except RuntimeError:
            print("Matplotlib unable to open display")
            raise
        # fill kwargs
        kwargs["cmap"] = cmap
        G = self.copy()
        if node_labels_to_integers:
            G = networkx.convert_node_labels_to_integers(G, label_attribute="name")
        tree = networkx.dfs_tree(G)
        pos = layout_function(tree, *func_args)
        with plt.style.context((plt_style)):
            if ax:
                fig = plt.gcf()
            else:
                if fig_height is None:
                    fig_height = fig_width
                fig, ax = plt.subplots(1, figsize=(fig_width, fig_height), dpi=dpi)

            if isinstance(color_nodes, str):
                from itertools import count

                groups = set(networkx.get_node_attributes(G, color_nodes).values())
                mapping = dict(zip(sorted(groups), count()))
                colors = [mapping[G.node[n][color_nodes]] for n in tree.nodes]
                colors = [discrete_cmap(len(groups), cmap).colors[i] for i in colors]

            paths_ = []
            for nt in tree:
                # choose nodes and color for each iteration
                nlist = [nt]
                label = "%s: %s" % (nt, G.nodes(data="name")[nt])
                if color_nodes:
                    node_color = [colors[nt]]
                else:
                    node_color = "#1f78b4"
                # draw the graph
                sc = networkx.draw_networkx_nodes(
                    tree,
                    pos=pos,
                    nodelist=nlist,
                    ax=ax,
                    node_color=node_color,
                    label=label,
                    **kwargs
                )
                paths_.extend(sc.get_paths())
            scatter = matplotlib.collections.PathCollection(paths_)
            networkx.draw_networkx_edges(tree, pos, ax=ax, arrows=arrows, **kwargs)
            if with_labels:
                networkx.draw_networkx_labels(G, pos, **kwargs)

            if legend:
                bbox = kwargs.get("bbox_to_anchor", (1, 1))
                legend1 = ax.legend(
                    title=color_nodes, bbox_to_anchor=bbox, markerscale=0.5
                )
                ax.add_artist(legend1)

            # clear axis
            ax.axis("off")

            fig, ax = save_and_show(
                fig=fig,
                ax=ax,
                save=save,
                show=show,
                close=close,
                filename=filename,
                file_format=file_format,
                dpi=dpi,
                axis_off=axis_off,
                extent=extent,
            )
            return fig, ax

    @property
    def core_graph(self):
        """Returns a copy of the ZoneGraph containing only core zones"""
        nodes = [i for i, data in self.nodes(data="core") if data]
        H = self.subgraph(nodes).copy()
        H.name = "Core_" + self.name
        return H

    @property
    def perim_graph(self):
        """Returns a copy of the ZoneGraph containing only perimeter zones"""
        nodes = [i for i, data in self.nodes(data="core") if not data]
        H = self.subgraph(nodes).copy()
        H.name = "Perim_" + self.name
        return H

    def info(self, node=None):
        """Print short summary of information for the graph or the node n.

        Args:
            node (any hashable): A node in the graph
        """
        return log(networkx.info(G=self, n=node))


def discrete_cmap(N, base_cmap=None):
    """Create an N-bin discrete colormap from the specified input map

    Args:
        N:
        base_cmap:
    """

    # Note that if base_cmap is a string or None, you can simply do
    #    return plt.cm.get_cmap(base_cmap, N)
    # The following works for string, None, or a colormap instance:
    import matplotlib.pyplot as plt
    import numpy as np

    base = plt.cm.get_cmap(base_cmap)
    color_list = base(np.linspace(0, 1, N))
    cmap_name = base.name + str(N)
    return matplotlib.colors.ListedColormap(color_list, cmap_name, N)
