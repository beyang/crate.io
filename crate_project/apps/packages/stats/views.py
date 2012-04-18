import collections
import datetime
import json
import time

import isoweek

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from packages.models import Package, Release, DownloadDelta, DownloadStatsCache

def stats_delta(request, slug):
    package = get_object_or_404(Package, name=slug)

    try:
        cached = DownloadStatsCache.objects.get(package=package)
    except DownloadStatsCache.DoesNotExist:
        pass
    else:
        return HttpResponse(json.dumps(cached.data), mimetype="application/json")

    releases = Release.objects.filter(package=package)
    releases = sorted(releases, key=lambda x: x.downloads)

    specific_releases = set([x.version for x in releases[-8:]])

    deltas = list(DownloadDelta.objects.filter(file__release__in=releases).order_by("date"))

    # @@@ Sanity Checks

    data = [{"name": "Other", "data": []}] + [{"name": release.version, "data": []} for release in releases if release.version in specific_releases]

    # Get First Week
    start_week = isoweek.Week.withdate(deltas[0].date)
    end_week =  isoweek.Week.thisweek()

    current = isoweek.Week(start_week.year, start_week.week)

    while current.year <= end_week.year and current.week < end_week.week:
        for x in data:
            x["data"].append({"x": int(time.mktime(current.day(0).timetuple()))})
        current = isoweek.Week(current.year, current.week + 1)

    _data = collections.defaultdict(dict)

    for d in deltas:
        target = int(time.mktime(isoweek.Week.withdate(d.date).day(0).timetuple()))
        _data[d.file.release.version if d.file.release.version in specific_releases else "Other"][target] = d.delta

    for i in xrange(0, len(data)):
        for j in xrange(0, len(data[i]["data"])):
            data[i]["data"][j]["y"] = _data[data[i]["name"] if data[i]["name"] in specific_releases else "Other"].get(data[i]["data"][j]["x"], 0)

    DownloadStatsCache.objects.create(package=package, data=data)

    return HttpResponse(json.dumps(data), mimetype="application/json")
