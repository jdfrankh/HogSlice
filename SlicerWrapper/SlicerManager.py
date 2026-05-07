



import os
import io
import traceback
import multiprocessing as _mp
import concurrent.futures
import math
import numpy as np
import trimesh
from shapely.ops import unary_union as _shapely_unary_union
from shapely.geometry import Polygon as _SP

import matplotlib
matplotlib.use('Agg')  # non-interactive backend — safe for off-screen PNG rendering
import matplotlib.pyplot as plt
import matplotlib.collections as mc

from runtime_paths import get_runtime_path
from SlicerWrapper.GcodePacket import Slice, GCODEPACKETTYPE

# Module-level mesh stored once per worker process via the pool initializer.
_worker_mesh     = None
_worker_bottom_z = None
_worker_top_z    = None


def _pool_init(mesh_bytes, bottom_z, top_z):
    """Deserialize the STL mesh once per worker process."""
    global _worker_mesh, _worker_bottom_z, _worker_top_z
    _worker_mesh     = trimesh.load(io.BytesIO(mesh_bytes), file_type='stl')
    _worker_bottom_z = bottom_z
    _worker_top_z    = top_z




class SlicerManager():

    eanblePngOutput = True
    # #printer specific constants, should be suplied as args
    
    extrudeWidth = .71
            
    support_infill_percent = 0
    supportInfill = 0
    
    infillPercent = 0
    infillSpeed = 0
    infillPower = 0

    numSideWalls = 1
    wallSpeed = 250
    wallPower = 50
    printSpeed = 250
    laserPower = 0
    
    topBottomSpacing = extrudeWidth
    topBottomWalls = 3
    radialMaxSpacing = 5
    topBottomDetectionHeight = .05


    delta = extrudeWidth/100.0 #delta for floating point comparison
    radialMaxSpacing = 5.0  # mm – max arc gap between adjacent radial lines at the perimeter

    # Written by sliceItem so callers can read part volume_cm3 after slicing
    last_volume_cm3 = 0.0


    def __init__(self):
        self.slicer = None

    def _polygon_area_mm2(self,lines):
        """Signed shoelace area (mm²) of a closed polygon described by a list of Line segments."""
        area = 0.0
        for line in lines:
            area += (line.p0.x * line.p1.y) - (line.p1.x * line.p0.y)
        return abs(area) * 0.5


    def _to_float(self,value, default):
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)
        
    def _renderLayerToPng(self, layer_slice, layer_index, total_layers, output_dir):
        #print(f"Layer Slice: {layer_slice}")
        
        """
        Render a single Slice to a PNG.

        Colours:
          - perimeter  → blue
          - sideWalls  → cyan
          - topBottom  → red
          - infill     → orange
          - support    → green

        File name: layer_XXXXX.png  (zero-padded to match total_layers width)
        """
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.set_aspect('equal')
        ax.set_facecolor('#1a1a1a')
        fig.patch.set_facecolor('#1a1a1a')

        def _add_lines(segments, color, lw=0.8):
            if not segments:
                return
            segs = [[(l.p0.x, l.p0.y), (l.p1.x, l.p1.y)] for l in segments]
            ax.add_collection(mc.LineCollection(segs, colors=color, linewidths=lw))

        _add_lines(layer_slice.getPacketLines(GCODEPACKETTYPE.SUPPORT),   '#44cc44', lw=0.6)   # green
        _add_lines(layer_slice.getPacketLines(GCODEPACKETTYPE.INFILL),    '#ffaa00', lw=0.6)   # orange
        _add_lines(layer_slice.getPacketLines(GCODEPACKETTYPE.TOPBOTTOM), '#ff3333', lw=0.8)   # red
        _add_lines(layer_slice.getPacketLines(GCODEPACKETTYPE.WALLS), '#00cccc', lw=0.8)   # cyan
        # Draw unlabelled tiny segments in dim blue, then overdraw labelled loops
        # with colour based on whether the loop is an external or internal surface.
        # _add_lines(layer_slice.perimeter, '#334466', lw=0.5)   # dim base
        
        #diag_pre = getattr(layer_slice, '_diagnostics', {'closed_loops': [], 'open_gaps': []})
        diag_pre = layer_slice.getDiagnosticsClosedLoop()
        #print(f"Amount of closed loops {len(diag_pre)}")
        for loop in diag_pre:
            loop_color = '#4477ff' if loop.get('internalOrExternal') else '#ff8800'  # blue=external, orange=internal
            _add_lines(loop.get('segs', []), loop_color, lw=1.1)

        # Draw open chain segments in dim red so their extent is visible
        #diag = getattr(layer_slice, '_diagnostics', {'closed_loops': [], 'open_gaps': []})
        diag = layer_slice.getDiagnosticsOpenChain()
        for gap_info in diag:
            _add_lines(gap_info['segs'], '#cc2222', lw=0.6)

        # Compute bounds from all geometry including open chains

        all_segs = layer_slice.getAllSegments()
        if all_segs:
            xs = [p for l in all_segs for p in (l.p0.x, l.p1.x)]
            ys = [p for l in all_segs for p in (l.p0.y, l.p1.y)]
            pad = max((max(xs) - min(xs)), (max(ys) - min(ys))) * 0.05 + 0.5
            ax.set_xlim(min(xs) - pad, max(xs) + pad)
            ax.set_ylim(min(ys) - pad, max(ys) + pad)
        else:
            ax.set_xlim(-1, 1)
            ax.set_ylim(-1, 1)

        width = str(len(str(total_layers)))
        label = f'Layer {layer_index + 1:{width}d}/{total_layers}  Z={layer_slice.zValue:.3f} mm'
        ax.set_title(label, color='white', fontsize=9)
        ax.tick_params(colors='#888888')
        for spine in ax.spines.values():
            spine.set_edgecolor('#444444')

        pad_digits = len(str(total_layers))
        fname = os.path.join(output_dir, f'layer_{layer_index + 1:0{pad_digits}d}.png')
        fig.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)


#This is the heavylifter that creates each outline
    def _slice_layer_worker(self, args):
        """Slice one layer using trimesh — runs in a worker process."""
        layer, layerThickness = args
        #print(args)
        z = _worker_bottom_z + layer * layerThickness
        is_surface = (z <= _worker_bottom_z + layerThickness) or (z >= _worker_top_z - layerThickness)

        
        #loop_label_idx    = 0   # only increments for substantial loops worth labelling

        sideWallsSettings  = {
            'extruderWidth' : self.extrudeWidth,
            'numSideWalls' : self.numSideWalls,
            'printSpeed' : self.printSpeed,
            'laserPower' : self.laserPower,
        }

        infillSettings = {
            'extruderWidth' : self.extrudeWidth,
            'infillPercent' : self.infillPercent,
            'infillPattern' : self.infillPattern,
            'printSpeed' : self.infillSpeed,
            'laserPower' : self.infillPower,

        }

        topBottomSettings = {
            'topBottomSpacing' : self.topBottomSpacing,
            'topBottomWalls' : self.topBottomWalls,
            'printSpeed' : self.wallSpeed,
            'laserPower' : self.wallPower

        }
        
        path3d = _worker_mesh.section(
                plane_origin=[0.0, 0.0, z],
                plane_normal=[0.0, 0.0, 1.0],
            )
        if path3d is not None:
            path2d, _ = path3d.to_planar()
            output = Slice(
                z, path2d, 
                sideWallSettings=sideWallsSettings, 
                infillSettings=infillSettings, 
                topBottomSettings=topBottomSettings, 
                isSurface=is_surface
            )

        try:
            pass

        except Exception as exc:
            print(f"[layer {layer + 1}] trimesh section error: {exc}")
        return layer, output



    def loadMesh(self, filename):
        """Load an STL (binary or ASCII) and return a trimesh.Trimesh object."""
        print(f"[loadMesh] Loading: {filename}")
        mesh = trimesh.load(filename, force='mesh')
        print(f"[loadMesh] Loaded: {len(mesh.faces)} triangles  bounds={mesh.bounds}")
        return mesh

    def writeGcodeFile(self, layer_slices, output_path):
        """Generate G-code from all sliced layers and write to output_path.

        Parameters
        ----------
        layer_slices : list of (layer_index, Slice)
            The ordered slice list produced by sliceItem.
        output_path : str
            Destination .gcode file path.
        """
        lines = []

        # --- Header -----------------------------------------------------------
        lines.append(";HogSlice G-code export")
        lines.append(f";layers      : {len(layer_slices)}")
        lines.append(f";extrudeWidth: {self.extrudeWidth}")
        lines.append(f";layerHeight : {round(layer_slices[1][1].zValue - layer_slices[0][1].zValue, 4) if len(layer_slices) > 1 else 'N/A'}")
        lines.append(f";infillPct   : {self.infillPercent}")
        lines.append(f";infillPattern: {self.infillPattern}")
        lines.append(f";numSideWalls: {self.numSideWalls}")
        lines.append(f";topBottomWalls: {self.topBottomWalls}")
        lines.append("")
        lines.append("G28 X0 Y0 Z0   ; home all axes")
        lines.append(f"M3 S{self.laserPower:.1f}         ; laser on at configured power")
        lines.append("")

        # --- Per-layer G-code -------------------------------------------------
        for layer_idx, layer_slice in layer_slices:
            layer_lines = layer_slice.buildGcode()
            if layer_lines:
                lines.append(f";layer {layer_idx + 1}/{len(layer_slices)}")
                lines.extend(layer_lines)
                lines.append("")

        # --- Footer -----------------------------------------------------------
        lines.append("M5            ; laser off")
        lines.append("G28 X0 Y0     ; return to home")
        lines.append(";End of file")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"[SlicerManager] G-code written to: {output_path}  ({len(lines)} lines)")
        return output_path

    def sliceItem(self, filename, layerThickness, infillPercent, power, speed, topBottomLayers=3, printerProfile=None, progressCallback=None):

  

        if printerProfile is not None:
           # self.bedWidth = self._to_float(getattr(printerProfile, "bedWidth", self.bedWidth), self.bedWidth)
            self.extrudeWidth = self._to_float(getattr(printerProfile, "extrudeWidth", self.extrudeWidth), self.extrudeWidth)
            
            self.support_infill_percent = self._to_float(getattr(printerProfile, "supportInfill", self.supportInfill * 100.0), self.supportInfill * 100.0)
            self.supportInfill = max(0.0, min(1.0, self.support_infill_percent / 100.0))
            
            self.infillPercent = self._to_float(getattr(printerProfile, "infillPercent", infillPercent), 0)
            self.infillPattern = getattr(printerProfile, "infillPattern", "Lines")
            self.infillSpeed = getattr(printerProfile, "infillSpeed", 100)

            self.numSideWalls = int(max(1, round(self._to_float(getattr(printerProfile, "numSideWalls", 1), 1))))
            self.printSpeed = int(max(1, round(self._to_float(getattr(printerProfile, "speed", speed), speed))))
            self.laserPower = self._to_float(getattr(printerProfile, "power", power), power)
            
            self.topBottomSpacing = self._to_float(getattr(printerProfile, "topBottomSpacing", self.extrudeWidth), self.extrudeWidth)
            self.topBottomWalls = self._to_float(getattr(printerProfile, "topBottomWalls", topBottomLayers ), 3)
            self.radialMaxSpacing = self._to_float(getattr(printerProfile, "radialMaxSpacing", 5.0), 5.0)
            self.topBottomDetectionHeight = self._to_float(getattr(printerProfile, "topBottomDetectionHeight", 0.5), 0.5)
        else:
            self.numSideWalls = 1
            self.printSpeed = int(max(1, round(self._to_float(speed, 900))))
            self.laserPower = self._to_float(power, 0)
            self.infillPattern = "Lines"
            self.topBottomSpacing = self.extrudeWidth
            self.topBottomDetectionHeight = 0.5

        self.delta = max(self.extrudeWidth, 1e-9)
        self.supportSpeed = int(max(1, round(self.printSpeed * 0.9)))
        self.travelSpeed = int(max(1, round(self.printSpeed * 3.0)))


        print("Slicing "+filename+" with layer thickness "+str(layerThickness)+" and infill percent "+str(infillPercent))

        # Output directory for layer PNGs — sibling folder next to the gcode file
        if self.eanblePngOutput:
            png_dir = os.path.join(os.path.dirname(os.path.abspath(filename)), 'layer_previews')
            print("[SlicerManager] PNG output dir:", png_dir)
            os.makedirs(png_dir, exist_ok=True)
            print("[SlicerManager] Created png_dir:", os.path.exists(png_dir))

        pool = None
        try:
            stl_path = get_runtime_path('enviroment.stl')
            print("[SlicerManager] Loading STL:", stl_path)
            mesh = self.loadMesh(stl_path)

            bottom_z = float(mesh.bounds[0][2])
            top_z    = float(mesh.bounds[1][2])
            total_layers = int(math.ceil((top_z - bottom_z) / layerThickness))
            print("[SlicerManager] Total layers:", total_layers)

            # Serialize mesh to STL bytes once — each worker deserializes its own copy
            buf = io.BytesIO()
            mesh.export(buf, file_type='stl')
            mesh_bytes = buf.getvalue()

            worker_args = [(layer, layerThickness) for layer in range(total_layers)]

            cpu_count = max(1, (_mp.cpu_count() or 1) - 1)  # leave one core for the UI
            print(f"[SlicerManager] Slicing {total_layers} layers using {cpu_count} workers")

            _pool_init(mesh_bytes, bottom_z, top_z)

            # --- Phase 1: parallel per-layer slicing (walls, top/bottom, infill geometry) ---
            # Each worker calls _slice_layer_worker which builds SideWall / TopBottom / Infill
            # segments for one layer.  ThreadPoolExecutor shares the module-level _worker_mesh
            # without serialization overhead; trimesh/numpy/shapely release the GIL so threads
            # run concurrently on multiple cores.
            _slice_results = [None] * total_layers
            print("[SlicerManager] Phase 1: slicing layers...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
                slice_futures = {
                    executor.submit(self._slice_layer_worker, arg): arg[0]
                    for arg in worker_args
                }
                completed = 0
                for future in concurrent.futures.as_completed(slice_futures):
                    layer_idx, slice_obj = future.result()
                    _slice_results[layer_idx] = (layer_idx, slice_obj)
                    completed += 1
                    if progressCallback:
                        progressCallback(int(completed / total_layers * 70))

            # Rebuild as an ordered list so all subsequent index-based passes work correctly
            layer_slices = [r for r in _slice_results if r is not None]
            self.layer_slices = layer_slices

            # --- Phase 2: cross-layer fill computation (sequential — order-dependent) ---
            print("[SlicerManager] Computing top/bottom surfaces...")
            top_bottom_walls = max(1, int(self.topBottomWalls))
            extrude_w  = max(self.extrudeWidth, 1e-6)
            num_walls  = max(1, int(self.numSideWalls))
            wall_inset = extrude_w * num_walls

            from collections import defaultdict as _dd

            layer_raw_unions  = []
            layer_fill_unions = []
            for _li, _ls in layer_slices:
                loops = _ls.getDiagnosticsClosedLoop() or []
                raw_polys = []

                # Group polygons by nesting depth (contain_count).
                # Even depth → EXTERNAL (solid material / inner islands): union in.
                # Odd  depth → INTERNAL (voids / letter holes):            difference out.
                level_groups = _dd(list)
                for lp in loops:
                    poly = lp.get('poly')
                    if not poly or not poly.is_valid or poly.is_empty:
                        continue
                    raw_polys.append(poly)
                    level_groups[lp.get('contain_count', 0)].append(poly)

                solid = _SP()
                for level in sorted(level_groups.keys()):
                    polys = level_groups[level]
                    inset_polys = []
                    inset_dist = -wall_inset if level % 2 == 0 else wall_inset
                    for p in polys:
                        try:
                            ip = p.buffer(inset_dist, join_style=2, mitre_limit=5.0)
                            if ip is not None and not ip.is_empty and ip.is_valid:
                                inset_polys.append(ip)
                        except Exception:
                            pass
                    if not inset_polys:
                        continue
                    level_union = _shapely_unary_union(inset_polys)
                    try:
                        if level % 2 == 0:
                            solid = solid.union(level_union)
                        else:
                            solid = solid.difference(level_union)
                    except Exception:
                        pass
                if solid is None or not solid.is_valid:
                    solid = _SP()

                layer_raw_unions.append(_shapely_unary_union(raw_polys) if raw_polys else _SP())
                layer_fill_unions.append(solid)

            print("[SlicerManager] Computing top/bottom fill regions...")
            fill_regions = []
            for j in range(total_layers):
                current = layer_fill_unions[j]
                if current is None or current.is_empty:
                    fill_regions.append(_SP())
                    continue
                region = _SP()
                far_below = layer_fill_unions[j - top_bottom_walls] if j >= top_bottom_walls else _SP()
                try:
                    bot = current.difference(far_below) if not far_below.is_empty else current.buffer(0)
                    if bot is not None and not bot.is_empty:
                        region = region.union(bot)
                except Exception:
                    pass
                far_above = layer_fill_unions[j + top_bottom_walls] if j + top_bottom_walls < total_layers else _SP()
                try:
                    top = current.difference(far_above) if not far_above.is_empty else current.buffer(0)
                    if top is not None and not top.is_empty:
                        region = region.union(top)
                except Exception:
                    pass
                if region is None or not region.is_valid:
                    region = _SP()
                fill_regions.append(region)

            # --- Phase 3: assign top/bottom and infill regions (parallel) ---
            # top/bottom and infill assignment are independent per layer — parallelise them.
            print("[SlicerManager] Assigning top/bottom and infill regions...")

            def _assign_regions(args):
                i, layer_idx, layer_slice = args
                if not fill_regions[i].is_empty:
                    layer_slice.setTopBottomRegions(fill_regions[i], layer_slice.zValue)
                fill_area = layer_fill_unions[i]
                if fill_area is None or fill_area.is_empty:
                    return
                tb_region = fill_regions[i]
                try:
                    infill_area = fill_area.difference(tb_region) if not tb_region.is_empty else fill_area
                    if infill_area is not None and not infill_area.is_empty:
                        layer_slice.setInfillRegion(infill_area, layer_slice.zValue)
                except Exception:
                    pass

            assign_args = [(i, layer_idx, layer_slice) for i, (layer_idx, layer_slice) in enumerate(layer_slices)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
                assign_futures = [executor.submit(_assign_regions, a) for a in assign_args]
                completed = 0
                for future in concurrent.futures.as_completed(assign_futures):
                    future.result()
                    completed += 1
                    if progressCallback:
                        progressCallback(70 + int(completed / total_layers * 20))

            # --- Phase 4: PNG rendering (optional, parallel) ---
            if self.eanblePngOutput:
                print("[SlicerManager] Rendering PNGs...")
                render_args = [
                    (layer_slice, layer_idx, total_layers, png_dir)
                    for layer_idx, layer_slice in layer_slices
                ]
                with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
                    png_futures = {
                        executor.submit(self._renderLayerToPng, *args): args[1]
                        for args in render_args
                    }
                    completed = 0
                    for future in concurrent.futures.as_completed(png_futures):
                        future.result()
                        completed += 1
                        if progressCallback:
                            progressCallback(90 + int(completed / total_layers * 10))

            if progressCallback:
                progressCallback(100)

        except Exception as e:
            print("[SlicerManager] Error slicing: " + str(e))
            traceback.print_exc()
            if pool is not None:
                pool.terminate()
                pool.join()
                pool = None
            if progressCallback:
                progressCallback(100)
        finally:
            if pool is not None:
                pool.close()
                pool.join()
                pool = None

