from pydantic import BaseModel, field_validator


class MassModel(BaseModel):
    """
    {
        "volume" : [ 0.003411385108378978, 0.003410724395374695, 0.0034120458213832646 ],
        "periphery" : [ 0.3551154530453107, 0.35506836484837767, 0.3551625412422433 ],
        "centroid" : [ -2.07609188073475E-9, ... ],
        "inertia" : [ 0.0994460593470721, ... ],
        "mass" : [ 9.585992154544929, 9.584199206938452, 9.587785102151415 ],
        "hasMass" : true,
        "massMissingCount" : 0,
        "principalInertia" : [ 0.09944605933465941, 0.09944605954654827, 0.19238058837442526 ],
        "principalAxes" : [ {
        "x" : -0.9702683926946019,
        "y" : -5.514078101148926E-9,
        "z" : -0.2420314982349062
        }, {
        "x" : -0.2420314982349062,
        "y" : -5.44073563520025E-10,
        "z" : 0.9702683926946021
        }, {
        "x" : 5.481818620570986E-9,
        "y" : -0.9999999999999999,
        "z" : 8.066832175421143E-10
        } ]
    }
    """
    volume: tuple[float, float, float]
    centroid: tuple[float, float, float, float, float, float, float, float, float]
    inertia: list[float]
    mass: tuple[float, float, float]
    principalInertia: tuple[float, float, float]
    principalAxes: list[dict[str, float]]

    @field_validator("principalAxes")
    def check_principal_axes(cls, v):
        if len(v) != 3:
            raise ValueError("Principal axes must have 3 elements")
