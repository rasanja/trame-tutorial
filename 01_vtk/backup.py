import os
import io
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify, html

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkFiltersCore import (
    vtkContourFilter,
    vtkGlyph3D,
    vtkMaskPoints,
    vtkThresholdPoints
)
from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
from vtkmodules.vtkIOLegacy import vtkStructuredPointsReader
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch
import vtkmodules.vtkRenderingOpenGL2

# -----------------------------------------------------------------------------
# VTK pipeline
# -----------------------------------------------------------------------------

renderer = vtkRenderer()
renderWindow = vtkRenderWindow()
renderWindow.AddRenderer(renderer)

renderWindowInteractor = vtkRenderWindowInteractor()
renderWindowInteractor.SetRenderWindow(renderWindow)
renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

colors = vtkNamedColors()

def load_vtk_file(file_obj):
    reader = vtkStructuredPointsReader()
    reader.SetReadFromInputString(True)
    reader.SetInputString(file_obj.getvalue())
    reader.Update()

    # Glyphs
    threshold = vtkThresholdPoints()
    threshold.SetInputConnection(reader.GetOutputPort())
    threshold.ThresholdByUpper(500)

    mask = vtkMaskPoints()
    mask.SetInputConnection(threshold.GetOutputPort())
    mask.SetOnRatio(5)

    cone = vtkConeSource()
    cone.SetResolution(11)
    cone.SetHeight(1)
    cone.SetRadius(0.25)

    cones = vtkGlyph3D()
    cones.SetInputConnection(mask.GetOutputPort())
    cones.SetSourceConnection(cone.GetOutputPort())
    cones.SetScaleFactor(0.4)
    cones.SetScaleModeToScaleByVector()

    lut = vtkLookupTable()
    lut.SetHueRange(.667, 0.0)
    lut.Build()

    scalarRange = [0] * 2
    cones.Update()
    scalarRange[0] = cones.GetOutput().GetPointData().GetScalars().GetRange()[0]
    scalarRange[1] = cones.GetOutput().GetPointData().GetScalars().GetRange()[1]

    vectorMapper = vtkPolyDataMapper()
    vectorMapper.SetInputConnection(cones.GetOutputPort())
    vectorMapper.SetScalarRange(scalarRange[0], scalarRange[1])
    vectorMapper.SetLookupTable(lut)

    vectorActor = vtkActor()
    vectorActor.SetMapper(vectorMapper)

    # Contours
    iso = vtkContourFilter()
    iso.SetInputConnection(reader.GetOutputPort())
    iso.SetValue(0, 175)

    isoMapper = vtkPolyDataMapper()
    isoMapper.SetInputConnection(iso.GetOutputPort())
    isoMapper.ScalarVisibilityOff()

    isoActor = vtkActor()
    isoActor.SetMapper(isoMapper)
    isoActor.GetProperty().SetRepresentationToWireframe()
    isoActor.GetProperty().SetOpacity(0.25)

    # Outline
    outline = vtkOutlineFilter()
    outline.SetInputConnection(reader.GetOutputPort())

    outlineMapper = vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtkActor()
    outlineActor.SetMapper(outlineMapper)
    outlineActor.GetProperty().SetColor(colors.GetColor3d("White"))

    renderer.RemoveAllViewProps()
    renderer.AddActor(outlineActor)
    renderer.AddActor(vectorActor)
    renderer.AddActor(isoActor)
    renderer.ResetCamera()
    renderWindow.Render()

# -----------------------------------------------------------------------------
# Trame GUI
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
ctrl = server.controller
state = server.state


@state.change("selected_file")
def handle_file_selected(selected_file, **kwargs):
    if selected_file and "content" in selected_file:
        file_content = selected_file["content"]
        file_name = selected_file.get("name", "unnamed.vtk")

        print(f"Loading file: {file_name}")  # Debug print

        # Create a temporary file-like object
        temp_file = io.BytesIO(file_content)

        # Pass the file-like object to load_vtk_file
        load_vtk_file(temp_file)
        ctrl.view_update()
    else:
        print("No file selected or invalid file information")


with SinglePageLayout(server) as layout:
    layout.title.set_text("VTK File Viewer")

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
            with vuetify.VRow(classes="fill-height", style="flex-direction: column;"):
                with vuetify.VCol(classes="flex-grow-1"):
                    view = vtk.VtkLocalView(renderWindow)
                    ctrl.view_update = view.update

                with vuetify.VCol(classes="flex-grow-0"):
                    vuetify.VFileInput(
                        label="Select VTK file",
                        accept=".vtk",
                        v_model=("selected_file", None),
                    )

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()