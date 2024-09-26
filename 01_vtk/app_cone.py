from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout

from trame.widgets import vtk, vuetify
from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch #noqa
import vtkmodules.vtkRenderingOpenGL2 #noqa

renderer = vtkRenderer()
renderWindow = vtkRenderWindow()
renderWindow.AddRenderer(renderer)

renderWindowInteractor = vtkRenderWindowInteractor()
renderWindowInteractor.SetRenderWindow(renderWindow)
renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

cone_source = vtkConeSource()
mapper = vtkPolyDataMapper()
mapper.SetInputConnection(cone_source.GetOutputPort())
actor = vtkActor()
actor.SetMapper(mapper)

renderer.AddActor(actor)
renderer.ResetCamera()

# -----------------------------------------------------------------------------
# Get a server to work with
# -----------------------------------------------------------------------------

server = get_server(client_type = "vue2")

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

ctrl = server.controller

with SinglePageLayout(server) as layout:
    # [...]

    with layout.content:
        with vuetify.VContainer(
            fluid=True,
            classes="pa-0 fill-height",
        ):
            html_view = vtk.VtkLocalView(renderWindow)
            #html_view = vtk.VtkRemoteView(renderWindow)
            # TODO: missing update when ready...
            ctrl.on_server_ready.add(html_view.update) 

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
