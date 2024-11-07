import os

from fontTools.ttLib.tables.C_P_A_L_ import Color
from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import vtk, vuetify, trame
from trame_vtk.modules.vtk.serializers import configure_serializer
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkFiltersCore import vtkContourFilter, vtkGlyph3D
from vtkmodules.vtkFiltersSources import vtkArrowSource  # Use arrow as the glyph
from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtk import vtkAxesActor
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
import vtkmodules.vtkRenderingOpenGL2  # noqa

# -----------------------------------------------------------------------------
# Constants / Global Initializations
# -----------------------------------------------------------------------------
CURRENT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
configure_serializer(encode_lut=True, skip_light=True) # Configure scene encoder
dataset_arrays = [] # Extract Array/Field information
default_array = {
    "text": "",
    "value": 0,
    "range": [0.0, 0.0],
    "type": None
}
default_min,default_max = 0,0
renderer,renderWindow,renderWindowInteractor = vtkRenderer(),vtkRenderWindow(),vtkRenderWindowInteractor()
mesh_lut, mesh_actor,mesh_mapper = vtkLookupTable(),vtkActor(),vtkDataSetMapper()
contour, contour_actor,contour_lut, contour_mapper = vtkContourFilter(), vtkActor(), vtkLookupTable(), vtkDataSetMapper()
axes, widget, contour_value,cube_axes = vtkAxesActor(),vtkOrientationMarkerWidget(), 0, vtkCubeAxesActor()
glyph_source, glyph_filter, glyph_mapper,glyph_actor =vtkArrowSource(), vtkGlyph3D(), vtkDataSetMapper(), vtkActor()

class Representation:
    Points = 0
    Wireframe = 1
    Surface = 2
    SurfaceWithEdges = 3


class LookupTable:
    Rainbow = 0
    Inverted_Rainbow = 1
    Greyscale = 2
    Inverted_Greyscale = 3


# -----------------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------------
def extract_array():
    global dataset_arrays, default_array, default_min, default_max
    fields = [
        (reader.GetOutput().GetPointData(), vtkDataObject.FIELD_ASSOCIATION_POINTS),
        (reader.GetOutput().GetCellData(), vtkDataObject.FIELD_ASSOCIATION_CELLS),
    ]
    for field in fields:
        field_arrays, association = field
        for i in range(field_arrays.GetNumberOfArrays()):
            array = field_arrays.GetArray(i)
            array_range = array.GetRange()
            dataset_arrays.append(
                {
                    "text": array.GetName(),
                    "value": i,
                    "range": list(array_range),
                    "type": association,
                }
            )
    default_array = dataset_arrays[0]
    default_min, default_max = default_array.get("range")

def vtk_test_pipeline():
    global renderer, renderWindow, renderWindowInteractor
    renderer = vtkRenderer()
    renderWindow = vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindowInteractor = vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderWindowInteractor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

def mesh_mapper_func():
    global mesh_actor, mesh_lut,mesh_mapper
    mesh_mapper = vtkDataSetMapper()
    mesh_actor = vtkActor()
    mesh_lut = mesh_mapper.GetLookupTable()

def glyph_mapper_func():
    global glyph_source, glyph_filter, glyph_mapper, reader
    glyph_filter = vtkGlyph3D()
    glyph_filter.SetSourceConnection(glyph_source.GetOutputPort())  # Set glyph shape
    glyph_filter.SetInputConnection(reader.GetOutputPort())  # Connect VTU data
    glyph_filter.SetScaleFactor(0.1)  # Adjust scale as needed for visibility

    # Step 4: Set up the mapper and actor for glyphs
    glyph_mapper = vtkDataSetMapper()
    glyph_mapper.SetInputConnection(glyph_filter.GetOutputPort())
    glyph_actor = vtkActor()
    glyph_actor.SetMapper(glyph_mapper)
    glyph_actor.SetVisibility(False)  # Start with glyph off (for toggling)

    # Add the actor to the renderer
    renderer.AddActor(glyph_actor)

def setup_contour_visualization():
    global contour, contour_actor, contour_lut,contour_mapper
    contour = vtkContourFilter()
    contour_mapper = vtkDataSetMapper()
    contour_actor = vtkActor()
    contour_lut = contour_mapper.GetLookupTable()

def setup_axes():
    global axes, widget, contour_value,cube_axes
    cube_axes = vtkCubeAxesActor()
    axes = vtkAxesActor()
    widget = vtkOrientationMarkerWidget()
    widget.SetOrientationMarker(axes)
    widget.SetInteractor(renderWindowInteractor)
    widget.SetViewport(0.0, 0.0, 0.1, 0.1)
    widget.SetEnabled(1)
    widget.InteractiveOff()
    contour_value = 0.5 * (default_max + default_min)

def load_data():
    global dataset_arrays, default_array, default_min, default_max,mesh_mapper,mesh_actor,mesh_lut
    global contour, contour_actor, contour_lut, contour_mapper,renderer,cube_axes,contour_mapper,contour_value,axes
    global glyph_filter, glyph_mapper, glyph_actor
    print("Dataset_arrays: ", dataset_arrays)
    print("Load_data called!!!!")
# Mesh
    mesh_mapper.SetInputConnection(reader.GetOutputPort())
    mesh_actor.SetMapper(mesh_mapper)
    renderer.AddActor(mesh_actor)

    # Mesh: Setup default representation to surface
    mesh_actor.GetProperty().SetRepresentationToSurface()
    mesh_actor.GetProperty().SetPointSize(1)
    mesh_actor.GetProperty().EdgeVisibilityOff()

    # Mesh: Apply rainbow color map
    mesh_lut.SetHueRange(0.666, 0.0)
    mesh_lut.SetSaturationRange(1.0, 1.0)
    mesh_lut.SetValueRange(1.0, 1.0)
    mesh_lut.Build()

    # Mesh: Color by default array
    mesh_mapper.SelectColorArray(default_array.get("text"))
    mesh_mapper.GetLookupTable().SetRange(default_min, default_max)
    if default_array.get("type") == vtkDataObject.FIELD_ASSOCIATION_POINTS:
        mesh_mapper.SetScalarModeToUsePointFieldData()
    else:
        mesh_mapper.SetScalarModeToUseCellFieldData()
    mesh_mapper.SetScalarVisibility(True)
    mesh_mapper.SetUseLookupTableScalarRange(True)

    # Contour
    contour.SetInputConnection(reader.GetOutputPort())
    contour_mapper.SetInputConnection(contour.GetOutputPort())
    contour_actor.SetMapper(contour_mapper)
    renderer.AddActor(contour_actor)

    # Contour: ContourBy default array
    contour_value = 0.5 * (default_max + default_min)
    renderer.SetBackground((82 / 255, 87 / 255, 110 / 255))
    contour.SetInputArrayToProcess(
        0, 0, 0, default_array.get("type"), default_array.get("text")
    )
    contour.SetValue(0, contour_value)

    # Contour: Setup default representation to surface
    contour_actor.GetProperty().SetRepresentationToSurface()
    contour_actor.GetProperty().SetPointSize(1)
    contour_actor.GetProperty().EdgeVisibilityOff()

    # Contour: Apply rainbow color map
    contour_lut.SetHueRange(0.666, 0.0)
    contour_lut.SetSaturationRange(1.0, 1.0)
    contour_lut.SetValueRange(1.0, 1.0)
    contour_lut.Build()

    # Contour: Color by default array
    contour_mapper.SelectColorArray(default_array.get("text"))
    contour_mapper.GetLookupTable().SetRange(default_min, default_max)
    if default_array.get("type") == vtkDataObject.FIELD_ASSOCIATION_POINTS:
        contour_mapper.SetScalarModeToUsePointFieldData()
    else:
        contour_mapper.SetScalarModeToUseCellFieldData()
    contour_mapper.SetScalarVisibility(True)
    contour_mapper.SetUseLookupTableScalarRange(True)

    # Glyph setup
    glyph_source = vtkArrowSource()  # Or use another glyph shape as needed
    glyph_filter = vtkGlyph3D()
    glyph_filter.SetSourceConnection(glyph_source.GetOutputPort())
    glyph_filter.SetInputConnection(reader.GetOutputPort())  # Connect VTU data
    glyph_filter.SetScaleFactor(0.1)  # Adjust for visibility

    glyph_mapper = vtkDataSetMapper()
    glyph_mapper.SetInputConnection(glyph_filter.GetOutputPort())
    glyph_actor = vtkActor()
    glyph_actor.SetMapper(glyph_mapper)
    glyph_actor.SetVisibility(False)  # Start with glyph off
    renderer.AddActor(glyph_actor)

    # Cube Axes
    renderer.AddActor(cube_axes)

    # Cube Axes: Boundaries, camera, and styling
    cube_axes.SetBounds(mesh_actor.GetBounds())
    cube_axes.SetCamera(renderer.GetActiveCamera())
    cube_axes.SetXLabelFormat("%6.1f")
    cube_axes.SetYLabelFormat("%6.1f")
    cube_axes.SetZLabelFormat("%6.1f")
    cube_axes.SetFlyModeToOuterEdges()
    renderer.AddActor(axes)
    renderer.ResetCamera()

def reset_pipeline():
    global renderer,renderWindow
    print("Resetting pipeline")
    # Remove all existing actors
    renderer.RemoveAllViewProps()
    # Reset camera and render window
    load_data()
    renderer.ResetCamera()
    renderWindow.Render()

def update_mesh_visibility(visibility):
    mesh_actor.SetVisibility(visibility)

def update_contour_visibility(visibility):
    contour_actor.SetVisibility(visibility)

def update_glyph_visibility(visibility):
    global glyph_actor
    glyph_actor.SetVisibility(visibility)

# Selection Change
def actives_change(ids):
    _id = ids[0]
    if _id == "1":  # Mesh
        state.active_ui = "mesh"
    elif _id == "2":  # Contour
        state.active_ui = "contour"
    elif _id == "3":  # Contour
        state.active_ui = "glyph"
    else:
        state.active_ui = "nothing"

# Visibility Change
def visibility_change(event):
    _id = event["id"]
    _visibility = event["visible"]

    if _id == "1":  # Mesh
        mesh_actor.SetVisibility(_visibility)
    elif _id == "2":  # Contour
        contour_actor.SetVisibility(_visibility)
    ctrl.view_update()

# Representation Callbacks
def update_representation(actor, mode):
    property = actor.GetProperty()
    if mode == Representation.Points:
        property.SetRepresentationToPoints()
        property.SetPointSize(5)
        property.EdgeVisibilityOff()
    elif mode == Representation.Wireframe:
        property.SetRepresentationToWireframe()
        property.SetPointSize(1)
        property.EdgeVisibilityOff()
    elif mode == Representation.Surface:
        property.SetRepresentationToSurface()
        property.SetPointSize(1)
        property.EdgeVisibilityOff()
    elif mode == Representation.SurfaceWithEdges:
        property.SetRepresentationToSurface()
        property.SetPointSize(1)
        property.EdgeVisibilityOn()

# Color Map Callbacks
def use_preset(actor, preset):
    lut = actor.GetMapper().GetLookupTable()
    if preset == LookupTable.Rainbow:
        lut.SetHueRange(0.666, 0.0)
        lut.SetSaturationRange(1.0, 1.0)
        lut.SetValueRange(1.0, 1.0)
    elif preset == LookupTable.Inverted_Rainbow:
        lut.SetHueRange(0.0, 0.666)
        lut.SetSaturationRange(1.0, 1.0)
        lut.SetValueRange(1.0, 1.0)
    elif preset == LookupTable.Greyscale:
        lut.SetHueRange(0.0, 0.0)
        lut.SetSaturationRange(0.0, 0.0)
        lut.SetValueRange(0.0, 1.0)
    elif preset == LookupTable.Inverted_Greyscale:
        lut.SetHueRange(0.0, 0.666)
        lut.SetSaturationRange(0.0, 0.0)
        lut.SetValueRange(1.0, 0.0)
    lut.Build()

def update_viewport_axes_visibility(visibility):
    global widget,axes
    widget.SetEnabled(visibility)
    print("update_axes_visibility!")
    axes.SetVisibility(visibility)
    ctrl.view_update()

# -----------------------------------------------------------------------------
# GUI elements
# -----------------------------------------------------------------------------
def standard_buttons():
    vuetify.VCheckbox(
        v_model=("cube_axes_visibility", True),
        on_icon="mdi-cube-outline",
        off_icon="mdi-cube-off-outline",
        classes="mx-1",
        hide_details=True,
        dense=True,
    )
    vuetify.VCheckbox(
        v_model=("viewport_axes_visibility", True),
        on_icon="mdi-axis-arrow",
        off_icon="mdi-axis-arrow-lock",
        classes="mx-1",
        hide_details=True,
        dense=True,
    )
    vuetify.VCheckbox( #for background
        v_model=("white_background", True),
        on_icon="mdi-white-balance-sunny",
        off_icon="mdi-weather-night",
        classes="mx-1",
        hide_details=True,
        dense=True,
    )
    vuetify.VCheckbox(
        v_model="$vuetify.theme.dark",
        on_icon="mdi-lightbulb-off-outline",
        off_icon="mdi-lightbulb-outline",
        classes="mx-1",
        hide_details=True,
        dense=True,
    )
    vuetify.VCheckbox(
        v_model=("viewMode", "local"),
        on_icon="mdi-lan-disconnect",
        off_icon="mdi-lan-connect",
        true_value="local",
        false_value="remote",
        classes="mx-1",
        hide_details=True,
        dense=True,
    )
    with vuetify.VBtn(icon=True, click="$refs.view.resetCamera()"):
        vuetify.VIcon("mdi-crop-free")

def pipeline_widget():
    trame.GitTree(
        sources=(
            "pipeline",
            [
                {"id": "1", "parent": "0", "visible": 1, "name": "Mesh"},
                {"id": "2", "parent": "1", "visible": 1, "name": "Contour"},
                {"id": "3", "parent": "2", "visible": 1, "name": "Glyph"},
            ],
        ),
        actives_change=(actives_change, "[$event]"),
        visibility_change=(visibility_change, "[$event]"),
    )

def ui_card(title, ui_name):
    with vuetify.VCard(v_show=f"active_ui == '{ui_name}'"):
        vuetify.VCardTitle(
            title,
            classes="grey lighten-1 py-1 grey--text text--darken-3",
            style="user-select: none; cursor: pointer",
            hide_details=True,
            dense=True,
        )
        content = vuetify.VCardText(classes="py-2")
    return content

def mesh_card():
    with ui_card(title="Mesh", ui_name="mesh"):
        vuetify.VCheckbox(
            v_model=("mesh_visibility", True),
            on_icon="mdi-eye-outline",
            off_icon="mdi-eye-closed",
            classes="mx-1",
            hide_details=True,
            dense=True,
        )
        vuetify.VSelect(
            # Representation
            v_model=("mesh_representation", Representation.Surface),
            items=(
                "representations",
                [
                    {"text": "Points", "value": 0},
                    {"text": "Wireframe", "value": 1},
                    {"text": "Surface", "value": 2},
                    {"text": "SurfaceWithEdges", "value": 3},
                ],
            ),
            label="Representation",
            hide_details=True,
            dense=True,
            outlined=True,
            classes="pt-1",
        )
        with vuetify.VRow(classes="pt-2", dense=True):
            with vuetify.VCol(cols="6"):
                vuetify.VSelect(
                    # Color By
                    label="Color by",
                    v_model=("mesh_color_array_idx", 0),
                    items=("array_list", dataset_arrays),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )
            with vuetify.VCol(cols="6"):
                vuetify.VSelect(
                    # Color Map
                    label="Colormap",
                    v_model=("mesh_color_preset", LookupTable.Rainbow),
                    items=(
                        "colormaps",
                        [
                            {"text": "Rainbow", "value": 0},
                            {"text": "Inv Rainbow", "value": 1},
                            {"text": "Greyscale", "value": 2},
                            {"text": "Inv Greyscale", "value": 3},
                        ],
                    ),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )
        vuetify.VSlider(
            # Opacity
            v_model=("mesh_opacity", 1.0),
            min=0,
            max=1,
            step=0.1,
            label="Opacity",
            classes="mt-1",
            hide_details=True,
            dense=True,
        )

def contour_card():
    with ui_card(title="Contour", ui_name="contour"):
        vuetify.VCheckbox(
            v_model=("contour_visibility", True),
            on_icon="mdi-eye-outline",
            off_icon="mdi-eye-closed",
            classes="mx-1",
            hide_details=True,
            dense=True,
        )
        vuetify.VSelect(
            # Contour By
            label="Contour by",
            v_model=("contour_by_array_idx", 0),
            items=("array_list", dataset_arrays),
            hide_details=True,
            dense=True,
            outlined=True,
            classes="pt-1",
        )
        vuetify.VSlider(
            # Contour Value
            v_model=("contour_value", contour_value),
            min=("contour_min", default_min),
            max=("contour_max", default_max),
            step=("contour_step", 0.01 * (default_max - default_min)),
            label="Value",
            classes="my-1",
            hide_details=True,
            dense=True,
        )
        vuetify.VSelect(
            # Representation
            v_model=("contour_representation", Representation.Surface),
            items=(
                "representations",
                [
                    {"text": "Points", "value": 0},
                    {"text": "Wireframe", "value": 1},
                    {"text": "Surface", "value": 2},
                    {"text": "SurfaceWithEdges", "value": 3},
                ],
            ),
            label="Representation",
            hide_details=True,
            dense=True,
            outlined=True,
            classes="pt-1",
        )
        with vuetify.VRow(classes="pt-2", dense=True):
            with vuetify.VCol(cols="6"):
                vuetify.VSelect(
                    # Color By
                    label="Color by",
                    v_model=("contour_color_array_idx", 0),
                    items=("array_list", dataset_arrays),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )
            with vuetify.VCol(cols="6"):
                vuetify.VSelect(
                    # Color Map
                    label="Colormap",
                    v_model=("contour_color_preset", LookupTable.Rainbow),
                    items=(
                        "colormaps",
                        [
                            {"text": "Rainbow", "value": 0},
                            {"text": "Inv Rainbow", "value": 1},
                            {"text": "Greyscale", "value": 2},
                            {"text": "Inv Greyscale", "value": 3},
                        ],
                    ),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )
        vuetify.VSlider(
            # Opacity
            v_model=("contour_opacity", 1.0),
            min=0,
            max=1,
            step=0.1,
            label="Opacity",
            classes="mt-1",
            hide_details=True,
            dense=True,
        )


def glyph_card():
    with ui_card(title="Glyph", ui_name="glyph"):
        # Toggle Visibility
        vuetify.VCheckbox(
            v_model=("glyph_visibility", False),
            on_icon="mdi-eye-outline",
            off_icon="mdi-eye-closed",
            classes="mx-1",
            hide_details=True,
            dense=True,
        )

        # Representation (e.g., Point, Surface, etc. if applicable for glyphs)
        vuetify.VSelect(
            v_model=("glyph_representation", Representation.Points),
            items=(
                "representations",
                [
                    {"text": "Points", "value": 0},
                    {"text": "Wireframe", "value": 1},
                    {"text": "Surface", "value": 2},
                    {"text": "SurfaceWithEdges", "value": 3},
                ],
            ),
            label="Representation",
            hide_details=True,
            dense=True,
            outlined=True,
            classes="pt-1",
        )

        # Color options (similar to mesh)
        with vuetify.VRow(classes="pt-2", dense=True):
            with vuetify.VCol(cols="6"):
                vuetify.VSelect(
                    label="Color by",
                    v_model=("glyph_color_array_idx", 0),
                    items=("array_list", dataset_arrays),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )
            with vuetify.VCol(cols="6"):
                vuetify.VSelect(
                    label="Colormap",
                    v_model=("glyph_color_preset", LookupTable.Rainbow),
                    items=(
                        "colormaps",
                        [
                            {"text": "Rainbow", "value": 0},
                            {"text": "Inv Rainbow", "value": 1},
                            {"text": "Greyscale", "value": 2},
                            {"text": "Inv Greyscale", "value": 3},
                        ],
                    ),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )

        # Scale Slider (specific to glyphs)
        vuetify.VSlider(
            v_model=("glyph_scale", 0.1),
            min=0.01,
            max=1.0,
            step=0.01,
            label="Scale",
            classes="mt-1",
            hide_details=True,
            dense=True,
        )

        # Opacity Slider
        vuetify.VSlider(
            v_model=("glyph_opacity", 1.0),
            min=0,
            max=1,
            step=0.1,
            label="Opacity",
            classes="mt-1",
            hide_details=True,
            dense=True,
        )

# Color By Callbacks
def color_by_array(actor, array):
    _min, _max = array.get("range")
    mapper = actor.GetMapper()
    mapper.SelectColorArray(array.get("text"))
    mapper.GetLookupTable().SetRange(_min, _max)
    if array.get("type") == vtkDataObject.FIELD_ASSOCIATION_POINTS:
        mesh_mapper.SetScalarModeToUsePointFieldData()
    else:
        mesh_mapper.SetScalarModeToUseCellFieldData()
    mapper.SetScalarVisibility(True)
    mapper.SetUseLookupTableScalarRange(True)




# -----------------------------------------------------------------------------
# Trame setup / Sequential starts here
# -----------------------------------------------------------------------------
vtk_test_pipeline()
# Read Data
reader = vtkXMLUnstructuredGridReader()
reader.SetFileName(os.path.join(CURRENT_DIRECTORY, "../data/unstructured3dQuads-CharData.vtu"))
reader.Update()

extract_array()
mesh_mapper_func()
glyph_mapper_func()
setup_contour_visualization()
setup_axes()
renderer.SetBackground((82/255, 87/255, 110/255))
load_data()
reset_pipeline()

server = get_server(client_type="vue2")
state, ctrl = server.state, server.controller
state.setdefault("active_ui", None)
state.setdefault("color_array_items", dataset_arrays)

state.setdefault("viewport_axes_visibility", True)
state.setdefault("mesh_visibility", True)
state.setdefault("contour_visibility", True)
state.setdefault("glyph_visibility", True)




# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------
with SinglePageWithDrawerLayout(server) as layout:
    layout.title.set_text("Viewer")

    with layout.toolbar:
        with vuetify.VFileInput(
            v_model=("selected_file", None),
            label="Choose file",
            hide_details=True,
            dense=True,
            outlined=True,
            style="max-width: 200px;",
        ):
            vuetify.VIcon("mdi-file-upload", slot="prepend")
        # toolbar components
        vuetify.VSpacer()
        vuetify.VDivider(vertical=True, classes="mx-2")
        standard_buttons()

    with layout.drawer as drawer:
        # drawer components
        drawer.width = 325
        pipeline_widget()
        vuetify.VDivider(classes="mb-2")
        mesh_card()
        contour_card()
        glyph_card()

    with layout.content:
        # content components
        with vuetify.VContainer(
            fluid=True,
            classes="pa-0 fill-height",
        ):
            view = vtk.VtkRemoteLocalView(
                renderWindow, namespace="view", mode="local", interactive_ratio=1
            )
            ctrl.view_update = view.update
            ctrl.view_reset_camera = view.reset_camera


# -----------------------------------------------------------------------------
# State Changes
# -----------------------------------------------------------------------------
@state.change("viewport_axes_visibility")
def toggle_viewport_axes_visibility(viewport_axes_visibility, **kwargs):
    update_viewport_axes_visibility(viewport_axes_visibility)

def set_background_color(color):
    renderer.SetBackground(color)
    ctrl.view_update()

@state.change("white_background")
def toggle_background_color(white_background, **kwargs):
    global cube_axes
    if white_background:
        set_background_color([5, 5, 5])  # White
        cube_axes.GetXAxesLinesProperty().SetColor(0, 0, 0)
        cube_axes.GetYAxesLinesProperty().SetColor(0, 0, 0)
        cube_axes.GetZAxesLinesProperty().SetColor(0, 0, 0)

        # Set the label colors to black for each axis
        cube_axes.GetTitleTextProperty(0).SetColor(0, 0, 0)  # X-axis label color
        cube_axes.GetTitleTextProperty(1).SetColor(0, 0, 0)  # Y-axis label color
        cube_axes.GetTitleTextProperty(2).SetColor(0, 0, 0)  # Z-axis label color

        # Set tick mark colors to black
        cube_axes.GetXAxesLinesProperty().SetColor(0, 0, 0)
        cube_axes.GetYAxesLinesProperty().SetColor(0, 0, 0)
        cube_axes.GetZAxesLinesProperty().SetColor(0, 0, 0)
    else:
        set_background_color([82/255, 87/255, 110/255])  # Dark grey (default VTK background)

@state.change("mesh_color_preset")
def update_mesh_color_preset(mesh_color_preset, **kwargs):
    use_preset(mesh_actor, mesh_color_preset)
    ctrl.view_update()

@state.change("contour_color_preset")
def update_contour_color_preset(contour_color_preset, **kwargs):
    use_preset(contour_actor, contour_color_preset)
    ctrl.view_update()


# Opacity Callbacks
@state.change("mesh_opacity")
def update_mesh_opacity(mesh_opacity, **kwargs):
    mesh_actor.GetProperty().SetOpacity(mesh_opacity)
    ctrl.view_update()


@state.change("contour_opacity")
def update_contour_opacity(contour_opacity, **kwargs):
    contour_actor.GetProperty().SetOpacity(contour_opacity)
    ctrl.view_update()


# Contour Callbacks
@state.change("contour_by_array_idx")
def update_contour_by(contour_by_array_idx, **kwargs):
    array = dataset_arrays[contour_by_array_idx]
    contour_min, contour_max = array.get("range")
    contour_step = 0.01 * (contour_max - contour_min)
    contour_value = 0.5 * (contour_max + contour_min)
    contour.SetInputArrayToProcess(0, 0, 0, array.get("type"), array.get("text"))
    contour.SetValue(0, contour_value)

    # Update UI
    state.contour_min = contour_min
    state.contour_max = contour_max
    state.contour_value = contour_value
    state.contour_step = contour_step

    # Update View
    ctrl.view_update()


@state.change("contour_value")
def update_contour_value(contour_value, **kwargs):
    contour.SetValue(0, float(contour_value))
    ctrl.view_update()


@state.change("mesh_representation")
def update_mesh_representation(mesh_representation, **kwargs):
    update_representation(mesh_actor, mesh_representation)
    ctrl.view_update()


@state.change("contour_representation")
def update_contour_representation(contour_representation, **kwargs):
    update_representation(contour_actor, contour_representation)
    ctrl.view_update()


@state.change("mesh_color_array_idx")
def update_mesh_color_by_name(mesh_color_array_idx, **kwargs):
    array = dataset_arrays[mesh_color_array_idx]
    color_by_array(mesh_actor, array)
    ctrl.view_update()


@state.change("contour_color_array_idx")
def update_contour_color_by_name(contour_color_array_idx, **kwargs):
    array = dataset_arrays[contour_color_array_idx]
    color_by_array(contour_actor, array)
    ctrl.view_update()

# Function to update the reader with the selected file
@state.change("selected_file")
def update_vtk_reader(selected_file, **kwargs):
    if selected_file:
        # Get the full path of the selected file
        print(f"curr dir is:{CURRENT_DIRECTORY}")
        file_path = os.path.join(CURRENT_DIRECTORY, "../data/" + selected_file['name'])

        # Update the reader with the new file path
        reader.SetFileName(file_path)
        reader.Update()
        reset_pipeline()
        ctrl.view_reset_camera()
        ctrl.view_reset_camera()
        ctrl.view_update()


@state.change("cube_axes_visibility")
def update_cube_axes_visibility(cube_axes_visibility, **kwargs):
    cube_axes.SetVisibility(cube_axes_visibility)
    ctrl.view_update()

@state.change("mesh_visibility")
def toggle_mesh_visibility(mesh_visibility, **kwargs):
    print("update mesh visibility!")
    update_mesh_visibility(mesh_visibility)
    ctrl.view_update()

@state.change("contour_visibility")
def toggle_contour_visibility(contour_visibility, **kwargs):
    print("update contour visibility!")
    update_contour_visibility(contour_visibility)

# Define toggle function for glyph visibility
@state.change("glyph_visibility")
def toggle_glyph(glyph_visibility, **kwargs):
    global glyph_actor
    print("update glyph visibility!")
    update_glyph_visibility(glyph_visibility)

# -----------------------------------------------------------------------------
# Main / Sequencial starts here
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
