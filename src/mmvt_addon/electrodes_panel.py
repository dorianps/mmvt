import bpy
import mmvt_utils as mu
import colors_utils as cu
import os.path as op
import glob
import time


def show_electrodes():
    if not ElecsPanel.addon.get_appearance_show_electrodes_layer(bpy.context.scene):
        ElecsPanel.addon.set_appearance_show_electrodes_layer(bpy.context.scene, True)


def leads_update(self, context):
    if ElecsPanel.addon is None or not ElecsPanel.init:
        return
    show_electrodes()
    prev_lead = ElecsPanel.current_lead
    ElecsPanel.current_lead = current_lead = bpy.context.scene.leads
    if current_lead == 'All':
        bpy.context.scene.show_only_lead = False
    else:
        for elc in ElecsPanel.electrodes:
            if mu.elec_group(elc, bpy.context.scene.bipolar) == current_lead:
                bpy.context.scene.electrodes = elc
                break
        bpy.context.scene.show_only_lead = True
    show_only_current_lead(self, context)
    electrodes_update(self, context)


# todo: Add a leads combobox
# todo: Move through the electrodes with the keyboard right and left
# todo: Solve the bugs with the wrong lead
def electrodes_update(self, context):
    if ElecsPanel.addon is None or not ElecsPanel.init:
        return
    show_electrodes()
    prev_electrode = ElecsPanel.current_electrode
    ElecsPanel.current_electrode = current_electrode = bpy.context.scene.electrodes
    bpy.context.scene.current_lead = ElecsPanel.groups[current_electrode]
    select_electrode(current_electrode)
    color_electrodes(current_electrode, prev_electrode)
    update_cursor()
    if prev_electrode != '':
        unselect_prev_electrode(prev_electrode)
        if ElecsPanel.groups[prev_electrode] != bpy.context.scene.current_lead:
             show_only_current_lead(self, context)
    if not ElecsPanel.lookup is None:
        loc = ElecsPanel.lookup[current_electrode]
        print_electrode_loc(loc)
        if bpy.context.scene.color_lables:
            plot_labels_probs(loc)


def select_electrode(current_electrode):
    for elec in ElecsPanel.electrodes:
        bpy.data.objects[elec].select = elec == current_electrode
    # ElecsPanel.addon.filter_electrode_func(bpy.context.scene.electrodes)


def color_electrodes(current_electrode, prev_electrode):
    color = bpy.context.scene.electrode_color
    ElecsPanel.addon.object_coloring(bpy.data.objects[current_electrode], tuple(color)) #cu.name_to_rgb('green'))
    if prev_electrode != current_electrode:
        ElecsPanel.addon.object_coloring(bpy.data.objects[prev_electrode], (1, 1, 1, 1))


def print_electrode_loc(loc):
    print('{}:'.format(ElecsPanel.current_electrode))
    for subcortical_name, subcortical_prob in zip(loc['subcortical_rois'], loc['subcortical_probs']):
        print('{}: {}'.format(subcortical_name, subcortical_prob))
    for cortical_name, cortical_prob in zip(loc['cortical_rois'], loc['cortical_probs']):
        print('{}: {}'.format(cortical_name, cortical_prob))


def update_cursor():
    current_electrode_obj = bpy.data.objects[ElecsPanel.current_electrode]
    bpy.context.scene.cursor_location = current_electrode_obj.location
    ElecsPanel.addon.freeview_panel.save_cursor_position()


def show_only_current_lead(self, context):
    if bpy.context.scene.show_only_lead:
        bpy.context.scene.current_lead = ElecsPanel.groups[ElecsPanel.current_electrode]
        for elec_obj in bpy.data.objects['Deep_electrodes'].children:
            elec_obj.hide = ElecsPanel.groups[elec_obj.name] != bpy.context.scene.current_lead
    else:
        for elec_obj in bpy.data.objects['Deep_electrodes'].children:
            elec_obj.hide = False


def plot_labels_probs(elc):
    ElecsPanel.addon.show_hide_hierarchy(do_hide=False, obj='Subcortical_meg_activity_map')
    ElecsPanel.addon.show_hide_hierarchy(do_hide=True, obj='Subcortical_fmri_activity_map')
    ElecsPanel.addon.clear_cortex()
    if len(elc['cortical_rois']) > 0:
        hemi = mu.get_obj_hemi(elc['cortical_rois'][0])
        if not hemi is None:
            # if no matplotlib should calculate the colors offline :(
            labels_data = dict(data=elc['cortical_probs'], colors=elc['cortical_colors'][:, :3], names=elc['cortical_rois'])
            ElecsPanel.addon.meg_labels_coloring_hemi(
                ElecsPanel.labels_names, ElecsPanel.labels_vertices, labels_data, ElecsPanel.faces_verts, hemi, 0)
        else:
            print("Can't get the rois hemi!")
    else:
        ElecsPanel.addon.clear_cortex()
    ElecsPanel.addon.clear_subcortical_regions()
    if len(elc['subcortical_rois']) > 0:
        for region, color in zip(elc['subcortical_rois'], elc['subcortical_colors'][:, :3]):
            ElecsPanel.addon.color_subcortical_region(region, color)


def unselect_prev_electrode(prev_electrode):
    prev_elc = bpy.data.objects.get(prev_electrode)
    if not prev_elc is None:
        ElecsPanel.addon.de_select_electrode(prev_elc, False)


def elecs_draw(self, context):
    layout = self.layout
    row = layout.row(align=True)
    row.operator(PrevElectrode.bl_idname, text="", icon='PREV_KEYFRAME')
    row.prop(context.scene, "leads", text="")
    row.operator(NextElectrode.bl_idname, text="", icon='NEXT_KEYFRAME')
    row = layout.row(align=True)
    row.operator(PrevElectrode.bl_idname, text="", icon='PREV_KEYFRAME')
    row.prop(context.scene, "electrodes", text="")
    row.operator(NextElectrode.bl_idname, text="", icon='NEXT_KEYFRAME')
    layout.prop(context.scene, 'show_only_lead', text="Show only the current lead")
    layout.prop(context.scene, 'color_lables', text="Color the relevant lables")
    if not bpy.context.scene.listen_to_keyboard:
        layout.operator(KeyboardListener.bl_idname, text="Listen to keyboard", icon='NEXT_KEYFRAME')
    else:
        layout.operator(KeyboardListener.bl_idname, text="Stop listen to keyboard", icon='NEXT_KEYFRAME')
    row = layout.row(align=True)
    row.label(text='Selected electrode color:')
    row = layout.row(align=True)
    row.label(text='             ')
    row.prop(context.scene, 'electrode_color', text='')
    row.label(text='             ')


class NextElectrode(bpy.types.Operator):
    bl_idname = 'ohad.next_electrode'
    bl_label = 'nextElectrodes'
    bl_options = {'UNDO'}

    def invoke(self, context, event=None):
        next_electrode()
        return {'FINISHED'}


def next_electrode():
    index = ElecsPanel.electrodes.index(bpy.context.scene.electrodes)
    if index < len(ElecsPanel.electrodes) - 1:
        next_elc = ElecsPanel.electrodes[index + 1]
        bpy.context.scene.electrodes = next_elc



class PrevElectrode(bpy.types.Operator):
    bl_idname = 'ohad.prev_electrode'
    bl_label = 'prevElectrodes'
    bl_options = {'UNDO'}

    def invoke(self, context, event=None):
        prev_electrode()
        return {'FINISHED'}


def prev_electrode():
    index = ElecsPanel.electrodes.index(bpy.context.scene.electrodes)
    if index > 0:
        prev_elc = ElecsPanel.electrodes[index - 1]
        bpy.context.scene.electrodes = prev_elc


class KeyboardListener(bpy.types.Operator):
    bl_idname = 'ohad.keyboard_listener'
    bl_label = 'keyboard_listener'
    bl_options = {'UNDO'}
    press_time = time.time()

    def modal(self, context, event):
        if time.time() - self.press_time > 1 and bpy.context.scene.listen_to_keyboard and \
                event.type not in ['TIMER', 'MOUSEMOVE', 'WINDOW_DEACTIVATE']:
            self.press_time = time.time()
            if event.type == 'LEFT_ARROW':
                prev_electrode()
            elif event.type == 'RIGHT_ARROW':
                next_electrode()
            else:
                pass
                # print(event.type)
        return {'PASS_THROUGH'}

    def invoke(self, context, event=None):
        if not bpy.context.scene.listener_is_running:
            context.window_manager.modal_handler_add(self)
            bpy.context.scene.listener_is_running = True
        bpy.context.scene.listen_to_keyboard = not bpy.context.scene.listen_to_keyboard
        return {'RUNNING_MODAL'}


bpy.types.Scene.show_only_lead = bpy.props.BoolProperty(
    default=False, description="Show only the current lead", update=show_only_current_lead)
bpy.types.Scene.color_lables = bpy.props.BoolProperty(
    default=False, description="Color the relevant lables")
bpy.types.Scene.listen_to_keyboard = bpy.props.BoolProperty(default=False)
bpy.types.Scene.listener_is_running = bpy.props.BoolProperty(default=False)
bpy.types.Scene.current_lead = bpy.props.StringProperty()
bpy.types.Scene.electrode_color = bpy.props.FloatVectorProperty(
    name="object_color", subtype='COLOR', default=(0, 0.5, 0), min=0.0, max=1.0, description="color picker")
    # size=2, subtype='COLOR_GAMMA', min=0, max=1)


class ElecsPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Electrodes localizator"
    addon = None
    init = False
    electrodes = []
    current_electrode = ''
    electrodes_locs = None
    lookup = None
    groups = {}

    def draw(self, context):
        elecs_draw(self, context)


def init(addon):
    ElecsPanel.addon = addon
    bipolar = bpy.context.scene.bipolar
    parent = bpy.data.objects.get('Deep_electrodes')
    if parent is None or len(parent.children) == 0:
        print("Can't register electrodes panel, no Deep_electrodes object!")
        return
    ElecsPanel.electrodes = [] if parent is None else [el.name for el in parent.children]
    ElecsPanel.electrodes.sort(key=mu.natural_keys)
    electrodes_items = [(elec, elec, '', ind) for ind, elec in enumerate(ElecsPanel.electrodes)]
    bpy.types.Scene.electrodes = bpy.props.EnumProperty(
        items=electrodes_items, description="electrodes", update=electrodes_update)
    groups = ['All'] + sorted(list(set([mu.elec_group(elc, bipolar) for elc in ElecsPanel.electrodes])))
    leads_items = [(group, group, '', ind) for ind, group in enumerate(groups)]
    bpy.types.Scene.leads = bpy.props.EnumProperty(
        items=leads_items, description="leads", update=leads_update)
    bpy.context.scene.electrodes = ElecsPanel.electrodes[0]
    ElecsPanel.current_electrode = ElecsPanel.electrodes[0]
    ElecsPanel.current_lead = groups[0]
    ElecsPanel.groups = create_groups_lookup_table(ElecsPanel.electrodes)
    loc_files = glob.glob(op.join(mu.get_user_fol(), '{}_{}_electrodes*.pkl'.format(mu.get_user(), bpy.context.scene.atlas)))
    if len(loc_files) > 0:
        # todo: there could be 2 files, one for bipolar and one for non bipolar
        ElecsPanel.electrodes_locs = mu.load(loc_files[0])
        ElecsPanel.lookup = create_lookup_table(ElecsPanel.electrodes_locs, ElecsPanel.electrodes)
        ElecsPanel.labels_names, ElecsPanel.labels_vertices = mu.load(
            op.join(mu.get_user_fol(), 'labels_vertices_{}.pkl'.format(bpy.context.scene.atlas)))
        # todo: Should be done only once in the main addon
        ElecsPanel.faces_verts = addon.load_faces_verts()
    else:
        print("Can't find loc file!")
    # addon.clear_filtering()
    addon.clear_colors_from_parent_childrens('Deep_electrodes')
    addon.clear_cortex()
    bpy.context.scene.show_only_lead = False
    bpy.context.scene.listen_to_keyboard = False
    bpy.context.scene.listener_is_running = False
    register()
    ElecsPanel.init = True
    print('Electrodes panel initialization completed successfully!')


def create_lookup_table(electrodes_locs, electrodes):
    lookup = {}
    for elc in electrodes:
        for electrode_loc in electrodes_locs:
            if electrode_loc['name'] == elc:
                lookup[elc] = electrode_loc
                break
    return lookup


def create_groups_lookup_table(electrodes):
    groups = {}
    for elc in electrodes:
        group, num = mu.elec_group_number(elc, bpy.context.scene.bipolar)
        groups[elc] = group
    return groups


def register():
    try:
        unregister()
        bpy.utils.register_class(ElecsPanel)
        bpy.utils.register_class(NextElectrode)
        bpy.utils.register_class(PrevElectrode)
        bpy.utils.register_class(KeyboardListener)
        print('Electrodes Panel was registered!')
    except:
        print("Can't register Electrodes Panel!")


def unregister():
    try:
        bpy.utils.unregister_class(ElecsPanel)
        bpy.utils.unregister_class(NextElectrode)
        bpy.utils.unregister_class(PrevElectrode)
        bpy.utils.unregister_class(KeyboardListener)
    except:
        print("Can't unregister Electrodes Panel!")

