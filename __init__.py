import bpy

bl_info = {
    "name": "Distribute and Shorten Strips",
    "author": "tintwotin",
    "version": (1, 0, 1),
    "blender": (2, 80, 0),
    "location": "Video Sequence Editor > Strip Menu (when a strip is selected)",
    "description": "Takes active strip's duration, divides it, then shortens and repositions selected strips (plus active) to fit sequentially, all on the active strip's channel.",
    "warning": "",
    "doc_url": "",
    "category": "Sequencer",
}

class ShortenAndDistributeStrips(bpy.types.Operator):
    """Takes active strip's duration, divides by selected count,
       then shortens and repositions all involved strips"""
    bl_idname = "vse.distribute_and_shorten_strips"
    bl_label = "Distribute and Shorten Strips"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.scene and
                context.scene.sequence_editor and
                context.scene.sequence_editor.active_strip)

    def execute(self, context):
        scene = context.scene
        sequencer = scene.sequence_editor

        if not sequencer:
            self.report({'WARNING'}, "No Video Sequence Editor found")
            return {'CANCELLED'}

        active_strip = sequencer.active_strip
        if not active_strip:
            self.report({'WARNING'}, "No active strip selected")
            return {'CANCELLED'}

        # Ensure other selected strips are distinct from the active strip
        selected_strips = [s for s in sequencer.sequences if s.select and s != active_strip]
        
        # Combine active strip and selected strips, ensuring no duplicates
        strips_to_process = list(set([active_strip] + selected_strips))

        if not strips_to_process: # Should not happen if active_strip exists
            self.report({'INFO'}, "No strips to process (active or selected)")
            return {'CANCELLED'}

        num_strips = len(strips_to_process)
        if num_strips == 0: # Redundant check if active_strip exists, but harmless
            self.report({'WARNING'}, "Zero strips to process")
            return {'CANCELLED'}

        original_start_frame = active_strip.frame_start
        original_channel = active_strip.channel # This is the target channel for all strips
        original_total_duration = active_strip.frame_final_duration

        if original_total_duration <= 0:
            self.report({'WARNING'}, "Active strip has zero or negative duration")
            return {'CANCELLED'}
            
        new_duration_per_strip = max(1, int(round(original_total_duration / num_strips)))

        current_frame_marker = original_start_frame
        
        # Sort strips by their original start time and channel to process them in a predictable visual order
        # This order determines which original strip becomes the first, second, etc., in the new sequence
        strips_to_process.sort(key=lambda s: (s.channel, s.frame_start))
        
        # Store names for re-selection, as strip objects can become invalid after modifications
        processed_strip_names = []
        original_active_strip_name = active_strip.name

        for strip in strips_to_process:
            processed_strip_names.append(strip.name)
            
            # Adjust strip properties
            strip.frame_final_duration = new_duration_per_strip
            strip.frame_start = current_frame_marker
            strip.channel = original_channel # Ensures all strips end up on the active strip's original channel
            
            current_frame_marker += new_duration_per_strip

        # Deselect all and reselect processed strips to give user feedback
        bpy.ops.sequencer.select_all(action='DESELECT')
        for name in processed_strip_names:
            s = sequencer.sequences.get(name)
            if s:
                s.select = True
        
        # Restore active strip status
        final_active_strip = sequencer.sequences.get(original_active_strip_name)
        if final_active_strip:
            sequencer.active_strip = final_active_strip
        elif processed_strip_names: # Fallback if original active got removed/renamed unexpectedly
             # Attempt to set the first processed strip (in sorted order) as active
             first_processed_strip_name = None
             # The `strips_to_process` was sorted. The first element in that sorted list
             # was the first one processed. We need its name.
             # We can find it by its new start frame (original_start_frame) and channel.
             for s_name in processed_strip_names:
                 s_cand = sequencer.sequences.get(s_name)
                 if s_cand and s_cand.frame_start == original_start_frame and s_cand.channel == original_channel:
                     first_processed_strip_name = s_name
                     break
             
             if first_processed_strip_name:
                 fallback_active = sequencer.sequences.get(first_processed_strip_name)
                 if fallback_active:
                    sequencer.active_strip = fallback_active
             elif sequencer.sequences.get(processed_strip_names[0]): # Fallback to just the first in the name list
                 sequencer.active_strip = sequencer.sequences.get(processed_strip_names[0])


        self.report({'INFO'}, f"Processed {num_strips} strips. New duration per strip: {new_duration_per_strip}. All moved to channel {original_channel+1}.") # Channel is 0-indexed internally, 1-indexed in UI
        
        # Force VSE update
        scene.frame_set(scene.frame_current) # Refresh UI
        # sequencer.sequences.update() # Usually not needed, frame_set is often enough

        return {'FINISHED'}

# --- Registration ---

def menu_func(self, context):
    self.layout.operator(ShortenAndDistributeStrips.bl_idname)

def register():
    print(f"Attempting to register: {ShortenAndDistributeStrips.bl_idname}")
    bpy.utils.register_class(ShortenAndDistributeStrips)
    
    if hasattr(bpy.types, "SEQUENCER_MT_strip"):
        bpy.types.SEQUENCER_MT_strip.append(menu_func)
        print(f"Appended to SEQUENCER_MT_strip: {ShortenAndDistributeStrips.bl_label}")
    else:
        print("WARNING: bpy.types.SEQUENCER_MT_strip not found. Menu item not added.")
        print("         This can happen if the script is run too early (e.g. 'Register' checkbox on text block)")
        print("         or in a Blender instance without the VSE UI fully initialized.")

def unregister():
    print(f"Attempting to unregister: {ShortenAndDistributeStrips.bl_idname}")
    if hasattr(bpy.types, "SEQUENCER_MT_strip"):
        try:
            bpy.types.SEQUENCER_MT_strip.remove(menu_func)
            print(f"Removed from SEQUENCER_MT_strip: {ShortenAndDistributeStrips.bl_label}")
        except ValueError:
            print(f"INFO: {ShortenAndDistributeStrips.bl_label} not found in SEQUENCER_MT_strip for removal.")
            pass 
    else:
        print("WARNING: bpy.types.SEQUENCER_MT_strip not found during unregistration.")

    try:
        bpy.utils.unregister_class(ShortenAndDistributeStrips)
        print(f"Unregistered class: {ShortenAndDistributeStrips.bl_idname}")
    except RuntimeError:
        print(f"INFO: {ShortenAndDistributeStrips.bl_idname} was not registered or already unregistered.")
        pass


if __name__ == "__main__":
    # When re-running from Text Editor, unregister previous version first
    try:
        unregister()
    except Exception as e:
        print(f"INFO: Unregister failed (likely first run or clean state): {e}")
        pass
    
    register()
