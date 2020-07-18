################################################################################
# Module: archetypal.template
# Description:
# License: MIT, see full license in LICENSE.txt
# Web: https://github.com/samuelduchesne/archetypal
################################################################################

import collections

from archetypal import log
from archetypal.template import MaterialBase, Unique, UniqueName, UmiBase


class GlazingMaterial(MaterialBase, metaclass=Unique):
    """Glazing Materials

    .. image:: ../images/template/materials-glazing.png

    """

    def __init__(
        self,
        Name,
        Density=2500,
        Conductivity=0,
        SolarTransmittance=0,
        SolarReflectanceFront=0,
        SolarReflectanceBack=0,
        VisibleTransmittance=0,
        VisibleReflectanceFront=0,
        VisibleReflectanceBack=0,
        IRTransmittance=0,
        IREmissivityFront=0,
        IREmissivityBack=0,
        DirtFactor=1.0,
        Type=None,
        Cost=0.0,
        Life=1,
        **kwargs
    ):
        """Initialize a GlazingMaterial object with parameters:

        Args:
            Name (str): The name of the GlazingMaterial.
            Density (float): A number representing the density of the material
                in kg/m3. This is essentially the mass of one cubic meter of the
                material.
            Conductivity (float): Thermal conductivity (W/m-K).
            SolarTransmittance (float): Transmittance at normal incidence
                averaged over the solar spectrum.
            SolarReflectanceFront (float): Front-side reflectance at normal
                incidence averaged over the solar spectrum.
            SolarReflectanceBack (float): Back-side reflectance at normal
                incidence averaged over the solar spectrum.
            VisibleTransmittance (float): Transmittance at normal incidence
                averaged over the solar spectrum and weighted by the response of
                the human eye.
            VisibleReflectanceFront (float): Front-side reflectance at normal
                incidence averaged over the solar spectrum and weighted by the
                response of the human eye.
            VisibleReflectanceBack (float): Back-side reflectance at normal
                incidence averaged over the solar spectrum and weighted by the
                response of the human eye.
            IRTransmittance (float): Long-wave transmittance at normal
                incidence.
            IREmissivityFront (float): Front-side long-wave emissivity.
            IREmissivityBack (float): Back-side long-wave emissivity.
            DirtFactor (float): This is a factor that corrects for the presence
                of dirt on the glass. Using a material with dirt correction
                factor < 1.0 in the construction for an interior window will
                result in an error message.
            Type: # todo: defined parameter
            Life: # todo: defined parameter
            **kwargs: keywords passed to the :class:`MaterialBase`
                constructor. For more info, see :class:`MaterialBase`.
        """
        super(GlazingMaterial, self).__init__(Name, **kwargs)
        self.Life = Life
        self.Cost = Cost
        self.Type = Type
        self.DirtFactor = DirtFactor
        self.IREmissivityBack = IREmissivityBack
        self.IREmissivityFront = IREmissivityFront
        self.IRTransmittance = IRTransmittance
        self.VisibleReflectanceBack = VisibleReflectanceBack
        self.VisibleReflectanceFront = VisibleReflectanceFront
        self.VisibleTransmittance = VisibleTransmittance
        self.SolarReflectanceBack = SolarReflectanceBack
        self.SolarReflectanceFront = SolarReflectanceFront
        self.SolarTransmittance = SolarTransmittance
        self.Density = Density
        self.Conductivity = Conductivity

    def __add__(self, other):
        """Overload + to implement self.combine."""
        return self.combine(other)

    def __hash__(self):
        return hash((self.__class__.__name__, self.Name))

    def __eq__(self, other):
        if not isinstance(other, GlazingMaterial):
            return False
        else:
            return all(
                [
                    self.Density == other.Density,
                    self.Conductivity == other.Conductivity,
                    self.SolarTransmittance == other.SolarTransmittance,
                    self.SolarReflectanceFront == other.SolarReflectanceFront,
                    self.SolarReflectanceBack == other.SolarReflectanceBack,
                    self.VisibleTransmittance == other.VisibleTransmittance,
                    self.VisibleReflectanceFront == other.VisibleReflectanceFront,
                    self.VisibleReflectanceBack == other.VisibleReflectanceBack,
                    self.IRTransmittance == other.IRTransmittance,
                    self.IREmissivityFront == other.IREmissivityFront,
                    self.IREmissivityBack == other.IREmissivityBack,
                    self.DirtFactor == other.DirtFactor,
                    self.Type == other.Type,
                    self.Cost == other.Cost,
                    self.Life == other.Life,
                ]
            )

    def combine(self, other, weights=None):
        """Combine two GlazingMaterial objects together.

        Args:
            other (GlazingMaterial): The other GlazingMaterial object to
                combine with.
        Returns:
            (GlazingMaterial): the combined GlazingMaterial object.
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

        meta = self._get_predecessors_meta(other)

        if not weights:
            log(
                'using GlazingMaterial density as weighting factor in "{}" '
                "combine.".format(self.__class__.__name__)
            )
            weights = [self.Density, other.Density]
        # iterate over attributes and apply either float_mean or str_mean.
        new_attr = {}
        for attr, value in self.__dict__.items():
            if attr not in [
                "Comments",
                "idf",
                "sql",
                "all_objects",
                "id",
                "_idf",
                "_sql",
            ]:
                if isinstance(value, (int, float)) or isinstance(other, (int, float)):
                    new_attr[attr] = UmiBase._float_mean(
                        self, other, attr=attr, weights=weights
                    )
                elif isinstance(value, str) or isinstance(other, str):
                    new_attr[attr] = UmiBase._str_mean(
                        self, other, attr=attr, append=False
                    )
                elif isinstance(value, list) or isinstance(other, list):
                    new_attr[attr] = getattr(self, attr) + getattr(other, attr)
                elif isinstance(value, collections.UserList) or isinstance(
                    other, collections.UserList
                ):
                    pass
                else:
                    raise NotImplementedError
        [new_attr.pop(key, None) for key in meta.keys()]  # meta handles these
        # keywords.
        # create a new object from combined attributes
        new_obj = self.__class__(**meta, **new_attr, idf=self.idf)
        new_obj._predecessors.extend(self.predecessors + other.predecessors)
        return new_obj

    def to_json(self):
        self.validate()  # Validate object before trying to get json format

        data_dict = collections.OrderedDict()

        data_dict["$id"] = str(self.id)
        data_dict["DirtFactor"] = self.DirtFactor
        data_dict["IREmissivityBack"] = self.IREmissivityBack
        data_dict["IREmissivityFront"] = self.IREmissivityFront
        data_dict["IRTransmittance"] = self.IRTransmittance
        data_dict["SolarReflectanceBack"] = self.SolarReflectanceBack
        data_dict["SolarReflectanceFront"] = self.SolarReflectanceFront
        data_dict["SolarTransmittance"] = self.SolarTransmittance
        data_dict["VisibleReflectanceBack"] = self.VisibleReflectanceBack
        data_dict["VisibleReflectanceFront"] = self.VisibleReflectanceFront
        data_dict["VisibleTransmittance"] = self.VisibleTransmittance
        data_dict["Conductivity"] = self.Conductivity
        data_dict["Cost"] = self.Cost
        data_dict["Density"] = self.Density
        data_dict["EmbodiedCarbon"] = self.EmbodiedCarbon
        data_dict["EmbodiedEnergy"] = self.EmbodiedEnergy
        data_dict["SubstitutionRatePattern"] = self.SubstitutionRatePattern
        data_dict["SubstitutionTimestep"] = self.SubstitutionTimestep
        data_dict["TransportCarbon"] = self.TransportCarbon
        data_dict["TransportDistance"] = self.TransportDistance
        data_dict["TransportEnergy"] = self.TransportEnergy
        data_dict["Category"] = self.Category
        data_dict["Comments"] = self.Comments
        data_dict["DataSource"] = self.DataSource
        data_dict["Name"] = UniqueName(self.Name)

        return data_dict

    def mapping(self):
        self.validate()

        return dict(
            id=self.id,
            DirtFactor=self.DirtFactor,
            IREmissivityBack=self.IREmissivityBack,
            IREmissivityFront=self.IREmissivityFront,
            IRTransmittance=self.IRTransmittance,
            SolarReflectanceBack=self.SolarReflectanceBack,
            SolarReflectanceFront=self.SolarReflectanceFront,
            SolarTransmittance=self.SolarTransmittance,
            VisibleReflectanceBack=self.VisibleReflectanceBack,
            VisibleReflectanceFront=self.VisibleReflectanceFront,
            VisibleTransmittance=self.VisibleTransmittance,
            Conductivity=self.Conductivity,
            Cost=self.Cost,
            Density=self.Density,
            EmbodiedCarbon=self.EmbodiedCarbon,
            EmbodiedEnergy=self.EmbodiedEnergy,
            SubstitutionRatePattern=self.SubstitutionRatePattern,
            SubstitutionTimestep=self.SubstitutionTimestep,
            TransportCarbon=self.TransportCarbon,
            TransportDistance=self.TransportDistance,
            TransportEnergy=self.TransportEnergy,
            Category=self.Category,
            Comments=self.Comments,
            DataSource=self.DataSource,
            Name=self.Name,
        )
