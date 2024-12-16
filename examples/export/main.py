from onshape_api.connect import Client
from onshape_api.log import LOGGER, LogLevel
from onshape_api.robot import Robot
from onshape_api.utilities.helpers import save_model_as_json

if __name__ == "__main__":
    LOGGER.set_file_name("ballbot.log")
    LOGGER.set_stream_level(LogLevel.INFO)
    client = Client()

    robot = Robot.from_url(
        name="ballbot",
        url="https://cad.onshape.com/documents/1f42f849180e6e5c9abfce52/w/0c00b6520fac5fada24b2104/e/c96b40ef586e60c182f41d29",
        client=client,
        max_depth=0,
        use_user_defined_root=False,
    )

    print(robot.assembly.model_dump(), type(robot.assembly))
    save_model_as_json(robot.assembly, "ballbot.json")

    robot.show_graph()
    robot.save()
