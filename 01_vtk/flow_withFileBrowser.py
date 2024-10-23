import os
import io
mask = None
vectorActor = None
iso = None
threshold = None

from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vtk, vuetify
from vtkmodules.vtkIOLegacy import vtkGenericDataObjectReader

from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonDataModel import vtkStructuredPoints
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
    global mask, vectorActor, iso
    reader = vtkStructuredPointsReader()
    reader.SetReadFromInputString(True)
    reader.SetInputString(file_obj.getvalue())  # This line is correct
    reader.Update()

    output = reader.GetOutput()
    if not output:
        print("Error: Unable to read VTK file")
        return

    global threshold
    threshold = vtkThresholdPoints()
    threshold.SetInputData(output)

    # Check if there's point data
    point_data = output.GetPointData()
    if point_data and point_data.GetNumberOfArrays() > 0:
        data_array = point_data.GetArray(0)
        if data_array:
            threshold.ThresholdByUpper(data_array.GetRange()[0])  # Use the minimum value as threshold

    # Outline
    outline = vtkOutlineFilter()
    outline.SetInputData(output)
    outlineMapper = vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())
    outlineActor = vtkActor()
    outlineActor.SetMapper(outlineMapper)
    outlineActor.GetProperty().SetColor(colors.GetColor3d("White"))

    renderer.RemoveAllViewProps()
    renderer.AddActor(outlineActor)

    # Check if there's point data
    point_data = output.GetPointData()
    if point_data and point_data.GetNumberOfArrays() > 0:
        # Assume the first array is the one we want to visualize
        data_array = point_data.GetArray(0)

        if data_array:
            # Threshold
            threshold = vtkThresholdPoints()
            threshold.SetInputData(output)
            threshold.ThresholdByUpper(data_array.GetRange()[0])  # Use the minimum value as threshold

            # Glyph
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

            vectorMapper = vtkPolyDataMapper()
            vectorMapper.SetInputConnection(cones.GetOutputPort())
            vectorMapper.SetScalarRange(data_array.GetRange())
            vectorMapper.SetLookupTable(lut)

            vectorActor = vtkActor()
            vectorActor.SetMapper(vectorMapper)

            renderer.AddActor(vectorActor)

            # Contours
            if output.GetDataObjectType() == vtkStructuredPoints().GetDataObjectType():
                iso = vtkContourFilter()
                iso.SetInputData(output)
                iso.SetValue(0, (data_array.GetRange()[0] + data_array.GetRange()[1]) / 2)  # Use middle value

                isoMapper = vtkPolyDataMapper()
                isoMapper.SetInputConnection(iso.GetOutputPort())
                isoMapper.ScalarVisibilityOff()

                isoActor = vtkActor()
                isoActor.SetMapper(isoMapper)
                isoActor.GetProperty().SetRepresentationToWireframe()
                isoActor.GetProperty().SetOpacity(0.25)

                renderer.AddActor(isoActor)

    renderer.ResetCamera()
    renderWindow.Render()



def apply_filters(threshold_value, opacity_value):
    global mask, vectorActor, iso
    if mask and vectorActor:
        point_data = mask.GetInput().GetPointData()
        if point_data and point_data.GetNumberOfArrays() > 0:
            data_array = point_data.GetArray(0)
            if data_array:
                data_range = data_array.GetRange()
                threshold = threshold_value / 100 * (data_range[1] - data_range[0]) + data_range[0]

                print(f"Applying threshold: {threshold}, opacity: {opacity_value}")  # Debug print

                # Update threshold filter
                mask.GetInputAlgorithm().ThresholdByUpper(threshold)

                # Update opacity of vector actor
                vectorActor.GetProperty().SetOpacity(opacity_value)

                # Update contour filter if applicable
                if iso:
                    iso.SetValue(0, threshold)

    renderWindow.Render()
    ctrl.view_update()
# -----------------------------------------------------------------------------
# Trame GUI
# -----------------------------------------------------------------------------

server = get_server(client_type="vue2")
ctrl = server.controller
state = server.state


state.threshold_value = 50
state.opacity_value = 1

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

@state.change("threshold_value", "opacity_value")
def update_filters(threshold_value, opacity_value, **kwargs):
    apply_filters(threshold_value, opacity_value)

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
                    vuetify.VSlider(
                        label="Threshold",
                        v_model=("threshold_value", 0),
                        min=0,
                        max=100,
                        step=1,
                        thumb_label="always",
                    )
                    vuetify.VSlider(
                        label="Opacity",
                        v_model=("opacity_value", 1),
                        min=0,
                        max=1,
                        step=0.1,
                        thumb_label="always",
                    )

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()