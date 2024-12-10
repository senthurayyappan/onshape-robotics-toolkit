def transform_w2b(m1, m2, m3):
    """
    Returns Ball (Phi) attributes
    """

    x = 0.323899 * m2 - 0.323899 * m3
    y = -0.374007 * m1 + 0.187003 * m2 + 0.187003 * m3
    z = 0.187003 * m1 + 0.187003 * m2 + 0.187003 * m3

    return x, y, z


def compute_motor_torques(Tx, Ty, Tz):
    """
    Parameters:
    ----------
    Tx: Torque along x-axis
    Ty: Torque along y-axis
    Tz: Torque along z-axis

    Returns:
    --------
            Ty
            T1
            |
            |
            |
            . _ _ _ _ Tx
           / \
          /   \
         /     \
        /       \
       T2       T3

    T1: Motor Torque 1
    T2: Motor Torque 2
    T3: Motor Torque 3
    """

    T1 = (0.3333) * (Tz - (2.8284 * Ty))
    T2 = (0.3333) * (Tz + (1.4142 * (Ty + 1.7320 * Tx)))
    T3 = (0.3333) * (Tz + (1.4142 * (Ty - 1.7320 * Tx)))

    return T1, T2, T3
