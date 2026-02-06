#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Draw a sign-in sheet showing what group/table students are assigned to.

Files are organized in the current directory like this:
    .
    ├── draw_sheets.py
    └── lab01
        ├── canvas.csv
        ├── groups015.png
        └── groups025.png
"""
# standard library
import os.path
import io
import argparse
import json
from urllib.request import Request, urlopen
# external dependencies
import numpy as np
import matplotlib.pyplot as plt

# configure help message formatting
class RawDescriptionDefaultsHelpFormatter(
        argparse.RawDescriptionHelpFormatter,
        argparse.ArgumentDefaultsHelpFormatter):
    pass

# Canvas API
API_URL = "https://umich.instructure.com/api/v1"
TOKEN = ""
COURSE_ID = 850281

# int for group numbers, 'I' for the instructor (optional), '.' for nothing
instructor = ""  # last name, first name
table_layout = [[ 1 , 'I', '.'],
                [ 2 , '.',  8 ],
                [ 3 , '.',  7 ],
                [ 4 ,  5 ,  6 ]]
tables = [table for row in table_layout
                for table in row
                if isinstance(table, int)]


def canvas_api(command):
    if not TOKEN:
        raise RuntimeError("No Canvas API access token defined.")
    request = Request(f"{API_URL}/{command}",
                      headers={"Authorization": f"Bearer {TOKEN}"})
    return urlopen(request)


def canvas_import_csv(lab, verbose=False):
    # the groups for each lab are defined in a group category on Canvas
    with canvas_api(f"courses/{COURSE_ID}/group_categories") as response:
        categories = json.load(response)
    try:
        category = next(category for category in categories
                        if category["name"].lower() == f"lab {lab:d}")
    except StopIteration:
        raise RuntimeError(f"Couldn't find groups for lab {lab:d} on Canvas.")

    # ask Canvas to export the groups for this lab as a CSV
    with canvas_api(f"group_categories/{category["id"]}/export") \
            as response:
        data = response.read()

    # save CSV on disk
    filename = os.path.join(f"lab{lab:02d}", "canvas.csv")
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as file:
        file.write(data)
    if verbose:
        print(f'CSV file written to "{filename}".')


def format_name(name):
    """Format "Smith, Emma Marie" as "Emma Smith"
    """
    lasts, firsts = name.split(",")
    first = firsts.strip().split(" ")[0]
    last = lasts.strip()  #.split(" ")[0]

    return f"__ {first:s} {last:s}"


def draw(names, groups, title="Groups", smallfont=18, bigfont=25):
    """Draw the group assignment on tables

    Args:
        names: list of the names of all students
        groups: list of the corresponding group numbers
    Returns:
        the created matplotlib figure
    """
    # create a grid of subplots based on table layout
    fig, axes = plt.subplot_mosaic(table_layout, figsize=(11, 8.5))

    fig.suptitle(title, fontsize=bigfont)

    for table in tables:
        # remove ticks and thicken spine for group axes
        ax = axes[table]
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_linewidth(2)
        # group number in the top left corner
        ax.text(0.05, 0.90, "{:d}".format(table),
                transform=ax.transAxes,
                fontsize=smallfont, ha="left", va="top")
        # the list of names
        ax.text(0.05, 0.70, "\n".join(sorted(names[groups == table])),
                transform=ax.transAxes,
                fontsize=smallfont, ha="left", va="top")

    # subplot for the instructor (me)
    if 'I' in axes.keys() and instructor:
        ax = axes['I']
        ax.set_axis_off()
        ax.text(0.5, 0.5, format_name(instructor),
                transform=ax.transAxes,
                fontsize=smallfont, ha="center", va="center")

    # TODO figure out why this sometimes leaves a margin on the right
    #      set margins by hand instead
    fig.tight_layout()

    return fig


# make sure we are in the right directory
os.chdir(os.path.dirname(__file__))

# already existing labs on disk
labs = [int(entry.removeprefix("lab")) for entry in os.listdir()
        if os.path.isdir(entry) and entry.startswith("lab")]
labs.sort()

# parse user arguments
description, epilog = __doc__.split("\n\n")
parser = argparse.ArgumentParser(description=description, epilog=epilog,
                                 formatter_class=RawDescriptionDefaultsHelpFormatter)
parser.add_argument("-v", "--verbose", action="store_true",
                    help="print status messages")
parser.add_argument("-f", "--force", action="store_true",
                    help="pull recent CSV from Canvas")
parser.add_argument("-e", "--extensions", nargs="+", default=["pdf", "png"],
                    metavar="ext", help="output formats")
parser.add_argument("-l", "--lab", type=int, default=-1 if TOKEN else max(labs),
                    metavar="number", help="-1 means next lab")
parser.add_argument("-s", "--sections", type=int, nargs="+", default=[15, 25],
                    metavar="section", help="your section numbers")
args = parser.parse_args()

# negative value means download the next lab
if args.lab == -1:
    lab = max(labs, default=0) + 1
    if args.verbose:
        print(f"Next lab is #{lab:d}.")
else:
    lab = args.lab

# download CSV if necessary
canvas_file = os.path.join(f"lab{lab:02d}", "canvas.csv")
if args.force or not os.path.exists(canvas_file):
    if args.verbose:
        print(f"Downloading lab {lab:d} from Canvas.")
    # TODO catch network error to simplify error message
    canvas_import_csv(lab, verbose=args.verbose)
else:
    if args.verbose:
        print(f'Using existing file "{canvas_file}".')

# parse CSV
dtype = [("name", "U50"), ("section", int), ("group", int)]
conv = {0: format_name,                  # name
        4: lambda name: name[-3:] or 0,  # sections
        5: lambda name: name[-1:] or 0}  # group_name
cols = list(sorted(conv.keys()))
names, sections, groups = np.loadtxt(canvas_file,
                                     delimiter=",", quotechar='"',
                                     dtype=dtype, converters=conv,
                                     skiprows=1, usecols=conv.keys(),
                                     unpack=True)

for section in args.sections:
    mask = sections == section
    fig = draw(names[mask], groups[mask],
               title=f"Groups for Lab {lab:02d} Section {section:03d}")
    for ext in args.extensions:
        filename = os.path.join(f"lab{lab:02d}", f"groups{section:03d}.{ext}")
        fig.savefig(filename)
        if args.verbose:
            print(f'Output written to "{filename}"')
    plt.close(fig)
