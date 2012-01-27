from haystack import indexes
from packages.models import Package

LICENSES = {
    "GNU General Public License (GPL)": "GPL",
    "GNU Library or Lesser General Public License (LGPL)": "LGPL",
    "GNU Affero General Public License v3": "Affero GPL",
    "Apache Software License": "Apache License",
    "ISC License (ISCL)": "ISC License",
    "Other/Proprietary License": "Other/Proprietary",
}


class PackageIndex(indexes.RealTimeSearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr="name", boost=1.5)
    summary = indexes.CharField(null=True)
    downloads = indexes.IntegerField(model_attr="downloads", indexed=False)
    url = indexes.CharField(model_attr="get_absolute_url", indexed=False)
    operating_systems = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    licenses = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    implementations = indexes.MultiValueField(null=True, faceted=True, facet_class=indexes.FacetMultiValueField)
    versions = indexes.MultiValueField(null=True)
    release_count = indexes.IntegerField(default=0)
    created = indexes.DateTimeField(null=True, faceted=True)

    def get_model(self):
        return Package

    def prepare(self, obj):
        data = super(PackageIndex, self).prepare(obj)

        if obj.latest:
            data["summary"] = obj.latest.summary
            data["created"] = obj.latest.created

            operating_systems = []
            licenses = []
            implementations = []

            for classifier in obj.latest.classifiers.all():
                if classifier.trove.startswith("License ::"):
                    # We Have a License for This Project
                    licenses.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Operating System ::"):
                    operating_systems.append(classifier.trove.rsplit("::", 1)[1].strip())
                elif classifier.trove.startswith("Programming Language :: Python :: Implementation ::"):
                    implementations.append(classifier.trove.rsplit("::", 1)[1].strip())

            if not licenses:
                licenses = ["Unknown"]

            licenses = [x for x in licenses if x not in ["OSI Approved"]]
            licenses = [LICENSES.get(x, x) for x in licenses]

            data["licenses"] = licenses

            if not operating_systems:
                operating_systems = ["Unknown"]
            data["operating_systems"] = operating_systems

            if not implementations:
                implementations = ["Unknown"]
            data["implementations"] = implementations

        # Pack in all the versions in decending order.
        releases = obj.releases.order_by("-order")
        data["versions"] = [release.version for release in releases if release.version]
        data["release_count"] = releases.count()

        # We want to scale the boost for this document based on how many downloads have
        #   been recorded for this package.
        # @@@ Might want to actually tier these values instead of percentage them.
        # Cap out downloads at 100k
        capped_downloads = min(data["downloads"], 10000)
        boost = capped_downloads / 10000.0
        data["_boost"] = 1.0 + boost

        return data
