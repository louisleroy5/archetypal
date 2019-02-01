import os
import time

import numpy as np
import osmnx as ox
import pandas as pd
from archetypal import log, NoCRSDefinedError, project_geom, settings
from shapely.geometry import box

import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import LightSource


def plot_map(gdf, bbox=None, crs=None, column=None, color=None, fig_height=6,
             fig_width=None, margin=0.02, equal_aspect=False,
             plot_graph=True, data_zorder=3, save=False, show=True,
             close=True, axis_off=True, legend=False, bgcolor='w',
             file_format='png', filename='temp', dpi=300, annotate=False,
             fig_title=None, **kwargs):
    """Plot a GeoDataFrame of geometry features.

    Args:
        gdf: (geopandas.GeoDataFrame): geometry features
        bbox (tuple): bounding box as north,south,east,west - if None will
            calculate from spatial extents of gdf. if passing a
            bbox, you probably also want to pass margin=0 to constrain it.
        crs (dict): projection coordinate system of the plot. Also assumed to be
            the coodinate system of the GeoDataFrame gdf
        column (str, np.array, pd.Series): The name of the dataframe column,
            np.array, or pd.Series to be plotted. If np.array or pd.Series
            are used then it must have same length as dataframe. Values are
            used to color the plot. Ignored if color is also set.
        color (str): If specified, all geometries will be colored uniformly.
        fig_height (float): matplotlib figure height in inches
        fig_width (float): matplotlib figure width in inches
        margin:
        plot_graph (bool): if True, plot the road network contained by the
            gdf's extent
        save (bool): if True, save the figure as an image file to disk
        show (bool): if True, show the figure
        close (bool): close the figure (only if show equals False) to prevent
            display
        axis_off (bool): if True turn off the matplotlib axis
        file_format (str): the format of the file to save (e.g., 'jpg', 'png',
            'svg', 'pdf')
        filename (str): the name of the file if saving
        dpi (int): the resolution of the image file if saving
        annotate (bool): if True, annotate the nodes in the figure
        **kwargs (dict, optional):

    Returns:
        fig, ax: tuple

    Keyword Args:
        network_type (str): what type of street network to get
        retain_all (bool): if True, return the entire graph even if it is not
            connected
        simplify (bool): if true, simplify the graph topology
        truncate_by_edge (bool): if True retain node if it's outside bbox but at
            least one of node's neighbors are within bbox
        clean_periphery (bool): if True (and simplify=True), buffer 0.5km to
            get a graph larger than requested, then simplify, then truncate
            it to requested spatial extent
        infrastructure (str): download infrastructure of given type (default
            is streets (ie, 'way["highway"]') but other infrastructures may
            be selected like power grids (ie, 'way["power"~"line"]'))
        edgecolor (str):
        facecolor (str):
        linewidth (float):
        markersize (float):
        alpha:
    """

    log('Begin plotting the map...')
    # if no crs is passed calculate from gdf
    if crs is None:
        crs = gdf.crs
        to_crs = crs
        # if the gdf's crs is none, then raise an error.
        if crs is None:
            raise NoCRSDefinedError('must provide the crs for this map')
    else:
        to_crs = crs

    # get north, south, east, west values either from bbox parameter or from the
    # spatial extent of the GeoDataFrame geometries
    if bbox is None:
        bbox_geom = box(*gdf.unary_union.bounds)
        west, south, east, north = project_geom(bbox_geom,
                                                from_crs=crs,
                                                to_latlon=True).bounds
    else:
        north, south, east, west = bbox

    # if caller did not pass in a fig_width, calculate it proportionately from
    # the fig_height and bounding box aspect ratio
    bbox_aspect_ratio = (north - south) / (east - west)
    if fig_width is None:
        fig_width = fig_height / bbox_aspect_ratio

    # if graph network
    if plot_graph:
        # configure osmnx with archetypal settings
        ox.config(data_folder=settings.data_folder,
                  logs_folder=settings.logs_folder,
                  imgs_folder=settings.imgs_folder,
                  cache_folder=settings.cache_folder,
                  use_cache=settings.use_cache,
                  log_file=settings.log_file,
                  log_console=settings.log_console,
                  log_level=settings.log_level,
                  log_name=settings.log_name,
                  log_filename=settings.log_filename)
        # use osmnx.graph_from_bbox()
        # first get kwargs
        network_type = kwargs.get('network_type', 'all_private')
        retain_all = kwargs.get('retain_all', False)
        simplify = kwargs.get('simplify', True)
        truncate_by_edge = kwargs.get('truncate_by_edge', False)
        name = kwargs.get('name', 'unnamed')
        timeout = kwargs.get('timeout', 180)
        memory = kwargs.get('memory', None)
        max_query_area_size = kwargs.get('max_query_area_size', 50 * 1000 * 50
                                         * 1000)
        clean_periphery = kwargs.get('clean_periphery', True)
        infrastructure = kwargs.get('infrastructure', 'way["highway"]')
        custom_filter = kwargs.get('custom_filter', None)
        #
        G = ox.graph_from_bbox(north, south, east, west,
                               network_type=network_type, simplify=simplify,
                               retain_all=retain_all,
                               truncate_by_edge=truncate_by_edge, name=name,
                               timeout=timeout, memory=memory,
                               max_query_area_size=max_query_area_size,
                               clean_periphery=clean_periphery,
                               infrastructure=infrastructure,
                               custom_filter=custom_filter)
        G = ox.project_graph(G, to_crs=to_crs)

        # plot the graph
        node_color = kwargs.get('node_color', '#66ccff')
        node_size = kwargs.get('node_size', 15)
        node_alpha = kwargs.get('node_alpha', 1)
        node_edgecolor = kwargs.get('node_edgecolor', 'none')
        node_zorder = kwargs.get('node_zorder', 1)
        edge_color = kwargs.get('edge_color', '#999999')
        edge_linewidth = kwargs.get('edge_linewidth', 1)
        edge_alpha = kwargs.get('edge_alpha', 1)
        use_geom = kwargs.get('use_geom', True)

        fig, ax = ox.plot_graph(G, bbox=bbox, fig_height=fig_height,
                                fig_width=fig_width, margin=margin,
                                axis_off=axis_off, equal_aspect=equal_aspect,
                                bgcolor=bgcolor, show=False, save=False,
                                close=False, file_format=file_format,
                                filename=filename, dpi=dpi, annotate=annotate,
                                node_color=node_color, node_size=node_size,
                                node_alpha=node_alpha,
                                node_edgecolor=node_edgecolor,
                                node_zorder=node_zorder, edge_color=edge_color,
                                edge_linewidth=edge_linewidth,
                                edge_alpha=edge_alpha, use_geom=use_geom)
    else:
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor=bgcolor)
        ax.set_facecolor(bgcolor)
    # from here, we are in the gdf projection coordinates
    # plot the map
    # Need to pop variables since we also pass kwargs as an argument
    cmap = kwargs.pop('cmap', None)
    # color is a function parameter
    categorical = kwargs.pop('categorical', False)
    # legend is a function parameter
    scheme = kwargs.pop('scheme', None)
    k = kwargs.pop('k', 5)
    vmin = kwargs.pop('vmin', None)
    vmax = kwargs.pop('vmax', None)
    markersize = kwargs.pop('markersize', 1)

    # plot the GeoDataFrame
    gdf.plot(column=column, cmap=cmap, color=color, ax=ax, zorder=data_zorder,
             categorical=categorical, markersize=markersize,
             figsize=(fig_width, fig_height), vmin=vmin,
             vmax=vmax, k=k, scheme=scheme, legend=legend, **kwargs)
    # adjust the axis margins and limits around the image and make axes
    # equal-aspect
    # get north, south, east, west values either from bbox parameter or from the
    # spatial extent of the GeoDataFrame geometries
    if bbox is None:
        bbox_geom = box(*gdf.unary_union.bounds)
        west, south, east, north = project_geom(bbox_geom,
                                                from_crs=crs,
                                                to_crs=to_crs).bounds
    else:
        north, south, east, west = bbox
    margin_ns = (north - south) * margin
    margin_ew = (east - west) * margin
    ax.set_ylim((south - margin_ns, north + margin_ns))
    ax.set_xlim((west - margin_ew, east + margin_ew))

    # configure axis appearance
    xaxis = ax.get_xaxis()
    yaxis = ax.get_yaxis()

    xaxis.get_major_formatter().set_useOffset(False)
    yaxis.get_major_formatter().set_useOffset(False)

    if equal_aspect:
        # make everything square
        ax.set_aspect('equal')
        fig.canvas.draw()
    else:
        # if the graph is not projected, conform the aspect ratio to not
        # stretch the plot
        if crs == settings.default_crs:
            coslat = np.cos((south + north) / 2. / 180. * np.pi)
            ax.set_aspect(1. / coslat)
            fig.canvas.draw()
    # if axis_off, turn off the axis display set the margins to zero and point
    # the ticks in so there's no space around the plot
    if axis_off:
        ax.axis('off')
        ax.margins(0)
        ax.tick_params(which='both', direction='in')
        xaxis.set_visible(False)
        yaxis.set_visible(False)
        fig.canvas.draw()

    if fig_title is not None:
        ax.set_title(fig_title)

    fig, ax = save_and_show(fig=fig, ax=ax, save=save, show=show, close=close,
                            filename=filename, file_format=file_format, dpi=dpi,
                            axis_off=axis_off, extent=None)
    return fig, ax


def save_and_show(fig, ax, save, show, close, filename, file_format, dpi,
                  axis_off, extent):
    """Save a figure to disk and show it, as specified.

    Args:
        extent:
        fig (figure):
        ax (axis):
        save (bool): whether to save the figure to disk or not
        show (bool): whether to display the figure or not
        close (bool): close the figure (only if show equals False) to prevent
            display
        filename (string): the name of the file to save
        file_format (string): the format of the file to save (e.g., 'jpg',
            'png', 'svg')
        dpi (int): the resolution of the image file if saving
        axis_off (bool): if True matplotlib axis was turned off by plot_graph so
            constrain the saved figure's extent to the interior of the axis

    Returns:
        (tuple) fig, ax
    """
    # save the figure if specified

    if save:
        start_time = time.time()

        # create the save folder if it doesn't already exist
        if not os.path.exists(settings.imgs_folder):
            os.makedirs(settings.imgs_folder)
        path_filename = os.path.join(settings.imgs_folder,
                                     os.extsep.join([filename, file_format]))

        if not isinstance(ax, (np.ndarray, list)):
            ax = [ax]
        if file_format == 'svg':
            for ax in ax:
                # if the file_format is svg, prep the fig/ax a bit for saving
                ax.axis('off')
                ax.set_position([0, 0, 1, 1])
                ax.patch.set_alpha(0.)
            fig.patch.set_alpha(0.)
            fig.savefig(path_filename, bbox_inches=0, format=file_format,
                        facecolor=fig.get_facecolor(), transparent=True)
        else:
            if extent is None:
                if len(ax) == 1:
                    if axis_off:
                        for ax in ax:
                            # if axis is turned off, constrain the saved
                            # figure's extent to the interior of the axis
                            extent = ax.get_window_extent().transformed(
                                fig.dpi_scale_trans.inverted())
                else:
                    extent = 'tight'
            fig.savefig(path_filename, dpi=dpi, bbox_inches=extent,
                        format=file_format, facecolor=fig.get_facecolor(),
                        transparent=True)
        log('Saved the figure to disk in {:,.2f} seconds'.format(time.time() -
                                                                 start_time))

    # show the figure if specified
    if show:
        start_time = time.time()
        plt.show()
        # fig.show()
        log('Showed the plot in {:,.2f} seconds'.format(time.time() -
                                                        start_time))
    # if show=False, close the figure if close=True to prevent display
    elif close:
        plt.close()

    return fig, ax


def plot_dhmin(model, axis_off=True, plot_demand=True, bbox=None, margin=0,
               show=True, save=False, close=False, dpi=300, file_format='png',
               fig_title=None, extent=None, legend=False, plot_built=True):
    """Plot power flows for model.

    Args:
        model:
        axis_off:
        plot_demand:
        bbox:
        margin:
        show:
        save:
        close:
        dpi:
        file_format:
        fig_title:
        none:
        extent:
        legend:

    Returns:

    """
    import dhmin

    if bbox is None:
        bbox = model.edges.geometry.total_bounds
        bbox = box(*bbox)
        # bbox = project_geom(bbox, from_crs={'init': 'epsg:2950'},
        #                     to_latlon=True)
        west, south, east, north = bbox.bounds
    else:
        west, south, east, north = bbox

    if plot_demand:
        # create a sperate figure with the original plotted demand
        plot_edges = model.edges.copy()
        plot_edges = plot_edges.loc[lambda x: x['peak'] > 0, :]
        fig, ax = plot_map(plot_edges, bbox=(north, south, east, west),
                           column='peak', plot_graph=False, show=False,
                           cmap='magma', margin=margin, close=False,
                           axis_off=axis_off, save=False,
                           fig_title='Original Peak Demand on Edges',
                           legend=legend)
        plot_init = model.vertices.loc[lambda x: x.init > 0, :]
        # plot initialized plants
        plot_init.plot(ax=ax, color='r', markersize=10,
                       legend=legend, zorder=4, label='Initialized Plants')
        # plot original street netowork behind the dh network
        model.edges.plot(ax=ax, linewidth=0.1, zorder=-1, color='grey',
                         legend=legend)
        # plot_edges.plot(column='peak', cmap='viridis', ax=ax, vmin=1)
        filename = '{}_original_peal_demand_on_edges'.format(model.name)
        save_and_show(fig=fig, ax=ax, save=save, show=show, close=False,
                      filename=filename, file_format=file_format, dpi=dpi,
                      axis_off=axis_off, extent=extent)

    if plot_built:
        pipe_x = dhmin.get_entities(model, ['x'])
        plot_edges = model.edges.copy()
        plot_edges = plot_edges.join(pipe_x,
                                     on=['Vertex1', 'Vertex2']).loc[lambda x:
                                                                    x.x == 1, :]

        fig, ax = plot_map(plot_edges, bbox=(north, south, east, west),
                           column='x', plot_graph=False, show=False,
                           cmap='magma', margin=margin, close=False,
                           axis_off=axis_off, save=False,
                           fig_title='Full extent of the network',
                           legend=legend)
        # plot original street netowork behind the dh network
        model.edges.plot(ax=ax, linewidth=0.1, zorder=-1, color='grey',
                         legend=legend)
        filename = '{}_all_built_pipes'.format(model.name)
        save_and_show(fig=fig, ax=ax, save=save, show=show, close=False,
                      filename=filename, file_format=file_format, dpi=dpi,
                      axis_off=axis_off, extent=extent)

    power_flows = dhmin.get_entities(model, ['Pin', 'Pot'])
    power_flows_grouped = power_flows.groupby(level='timesteps')

    power_input = dhmin.get_entity(model, 'Q')
    power_input_grouped = power_input.groupby(level='timesteps')

    for i, (name, group) in enumerate(power_flows_grouped):
        plot_edges = model.edges.copy()
        plot_edges = plot_edges.join(group.reset_index(level=2),
                                     on=['Vertex1', 'Vertex2'])
        plot_edges = plot_edges.loc[lambda x: x['Pin'] > 0, :]
        fig, ax = plot_map(plot_edges, bbox=(north, south, east, west),
                           column='Pin', plot_graph=False, show=False,
                           cmap='viridis', margin=margin,
                           axis_off=axis_off, save=False, close=False,
                           fig_title='Timestep_{}'.format(name), legend=legend)

        Q = power_input_grouped.get_group(name)['Q']
        plot_nodes = model.vertices.copy()
        plot_nodes = plot_nodes.join(Q.reset_index(level=1))

        msizes = [30 if m > 0 else 0 for m in plot_nodes['Q']]
        plot_nodes.plot(column='Q', cmap='OrRd', ax=ax, markersize=msizes,
                        vmin=1, zorder=3, legend=legend)
        # plot original street netowork behind the dh network
        model.edges.plot(ax=ax, linewidth=0.1, zorder=-1, color='grey',
                         legend=legend)
        filename = '{}_Timestep_{}'.format(model.name, name)
        save_and_show(fig=fig, ax=ax, save=save, show=show, close=close,
                      filename=filename, file_format=file_format, dpi=dpi,
                      axis_off=axis_off, extent=extent)


def plot_energyprofile(energyprofile, kind='polygon', axis_off=True, cmap=None,
                       fig_height=None, fig_width=6, show=True, view_angle=-60,
                       save=False, close=False, dpi=300, file_format='png',
                       color=None, axes=None, vmin=None, vmax=None,
                       filename=None, **kwargs):
    """

    Args:
        energyprofile:
        axis_off:
        cmap:
        fig_height:
        fig_width:
        show:
        save:
        close:
        dpi:
        file_format:
        color:
        axes:
        vmin:
        vmax:
        filename:
        **kwargs:

    Returns:

    """
    if energyprofile.empty:
        warnings.warn("The EnergyProgile you are attempting to plot is "
                      "empty. Nothing has been displayed.", UserWarning)
        return axes

    from mpl_toolkits.mplot3d import Axes3D
    import matplotlib.pyplot as plt

    if isinstance(energyprofile.index, pd.MultiIndex):
        groups = energyprofile.groupby(level=0)
        nax = len(groups)
    else:
        nax = 1
        groups = [('unnamed', energyprofile)]

    if fig_height is None:
        fig_height = fig_width * nax

    # Set up plot
    fig, axes = plt.subplots(nax, 1, subplot_kw=dict(projection='3d'),
                             figsize=(fig_width, fig_height), dpi=dpi)
    if not isinstance(axes, np.ndarray):
        axes = [axes]

    for ax, (name, profile) in zip(axes, groups):
        values = profile.values

        vmin = values.min() if vmin is None else vmin
        vmax = values.max() if vmax is None else vmax

        facecolor = kwargs.pop('facecolor', None)
        if color is not None:
            facecolor = color

        if kind == 'polygon':
            z = values.reshape(365, 24)
            nrows, ncols = z.shape
            xs = np.linspace(0, 23, ncols)
            # y = np.linspace(0, 364, nrows)
            # The ith polygon will appear on the plane y = zs[i]
            zs = np.linspace(0, 364, nrows)
            verts = []
            for i in zs:
                ys = z[int(i), :]
                verts.append(polygon_under_graph(xs, ys))

            plot_poly_collection(ax, verts, zs,
                                 edgecolors=kwargs.get('edgecolors', None),
                                 facecolors=kwargs.get('facecolors', None),
                                 linewidths=kwargs.get('linewidths', None),
                                 cmap=cmap)
        elif kind == 'surface':
            z = values.reshape(365, 24)
            nrows, ncols = z.shape
            x = np.linspace(1, 24, ncols)
            y = np.linspace(1, 365, nrows)
            x, y = np.meshgrid(x, y)
            plot_surface(ax, x, y, z, cmap=cmap, **kwargs)
        else:
            raise NameError('plot kind "{}" is not supported'.format(kind))

        if filename is None:
            filename = 'unnamed'

        # set the extent of the figure
        ax.set_xlim3d(-1, 24)
        ax.set_xlabel('X')
        ax.set_ylim3d(-1, 365)
        ax.set_ylabel('Y')
        ax.set_zlim3d(vmin, vmax)
        ax.set_zlabel('Z')

        # configure axis appearance
        xaxis = ax.xaxis
        yaxis = ax.yaxis
        zaxis = ax.zaxis

        xaxis.get_major_formatter().set_useOffset(False)
        yaxis.get_major_formatter().set_useOffset(False)
        zaxis.get_major_formatter().set_useOffset(False)

        # if axis_off, turn off the axis display set the margins to zero and
        # point
        # the ticks in so there's no space around the plot
        if axis_off:
            ax.axis('off')
            ax.margins(0)
            ax.tick_params(which='both', direction='in')
            xaxis.set_visible(False)
            yaxis.set_visible(False)
            zaxis.set_visible(False)
            fig.canvas.draw()
        if view_angle is not None:
            ax.view_init(30, view_angle)
            ax.set_proj_type(kwargs.get('proj_type', 'persp'))
            fig.canvas.draw()
    fig, axes = save_and_show(fig=fig, ax=axes, save=save, show=show,
                              close=close, filename=filename,
                              file_format=file_format, dpi=dpi,
                              axis_off=axis_off, extent=None)
    return fig, axes


def plot_poly_collection(ax, verts, zs=None, color=None, cmap=None,
                         vmin=None, vmax=None, **kwargs):
    from matplotlib.collections import PolyCollection

    # if None in zs:
    #     zs = None

    # color=None overwrites specified facecolor/edgecolor with default color
    if color is not None:
        kwargs['color'] = color
    import matplotlib as mpl
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

    poly = PolyCollection(verts, **kwargs)
    if zs is not None:
        poly.set_array(np.asarray(zs))
        poly.set_cmap(cmap)
        poly.set_clim(vmin, vmax)

    ax.add_collection3d(poly, zs=zs, zdir='y')
    # ax.autoscale_view()
    return poly


def plot_surface(ax, x, y, z, cmap=None, **kwargs):

    if cmap is None:
        cmap = cm.gist_earth

    ls = LightSource(270, 45)
    # To use a custom hillshading mode, override the built-in shading and pass
    # in the rgb colors of the shaded surface calculated from "shade".
    rgb = ls.shade(z, cmap=cm.get_cmap(cmap), vert_exag=0.1, blend_mode='soft')
    surf = ax.plot_surface(x, y, z, rstride=1, cstride=1, facecolors=rgb,
                           linewidth=0, antialiased=False, shade=False)
    return surf


def polygon_under_graph(xlist, ylist):
    """Construct the vertex list which defines the polygon filling the space under
    the (xlist, ylist) line graph.  Assumes the xs are in ascending order."""
    return [(xlist[0], 0.), *zip(xlist, ylist), (xlist[-1], 0.)]


def plot_raster_from_array(data, extent, bbox=None, crs=None,
                           fig_height=6, fig_width=None, margin=0.02,
                           equal_aspect=False, save=False, show=True,
                           close=True, axis_off=True, legend=False, bgcolor='w',
                           file_format='png', filename='temp', dpi=300,
                           fig_title=None, **kwargs):
    # get north, south, east, west values either from bbox parameter or from the
    # spatial extent of the GeoTiff
    if bbox is None:
        north, south, east, west = extent
    else:
        north, south, east, west = bbox

    # if caller did not pass in a fig_width, calculate it proportionately from
    # the fig_height and bounding box aspect ratio
    bbox_aspect_ratio = (north - south) / (east - west)
    if fig_width is None:
        fig_width = fig_height / bbox_aspect_ratio

    fig, ax = plt.subplots(figsize=(fig_width, fig_height), facecolor=bgcolor)
    ax.set_facecolor(bgcolor)

    maxy, miny, maxx, minx = extent
    # Calculate meshgrid
    x = np.linspace(minx, maxx, data.shape[1])
    y = np.linspace(miny, maxy, data.shape[0])
    xx, yy = np.meshgrid(x, y)

    # plot
    kk = ax.pcolormesh(xx, yy, data, cmap=plt.cm.jet)

    # adjust the axis margins and limits around the image and make axes
    # equal-aspect
    # get north, south, east, west values either from bbox parameter or from the
    # spatial extent of the GeoDataFrame geometries

    margin_ns = (north - south) * margin
    margin_ew = (east - west) * margin
    ax.set_ylim((south - margin_ns, north + margin_ns))
    ax.set_xlim((west - margin_ew, east + margin_ew))

    # configure axis appearance
    xaxis = ax.get_xaxis()
    yaxis = ax.get_yaxis()

    xaxis.get_major_formatter().set_useOffset(False)
    yaxis.get_major_formatter().set_useOffset(False)

    if equal_aspect:
        # make everything square
        ax.set_aspect('equal')
        fig.canvas.draw()
    else:
        # if the graph is not projected, conform the aspect ratio to not
        # stretch the plot
        if crs == settings.default_crs:
            coslat = np.cos((south + north) / 2. / 180. * np.pi)
            ax.set_aspect(1. / coslat)
            fig.canvas.draw()
    # if axis_off, turn off the axis display set the margins to zero and point
    # the ticks in so there's no space around the plot
    if axis_off:
        ax.axis('off')
        ax.margins(0)
        ax.tick_params(which='both', direction='in')
        xaxis.set_visible(False)
        yaxis.set_visible(False)
        fig.canvas.draw()

    if fig_title is not None:
        ax.set_title(fig_title)

    if legend:
        fig.colorbar(kk, ax=ax)
    fig, ax = save_and_show(fig=fig, ax=ax, save=save, show=show, close=close,
                            filename=filename, file_format=file_format, dpi=dpi,
                            axis_off=axis_off, extent=None)

    return fig, ax
