from statistics import quantiles
from time import perf_counter

from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings

class Command(BaseCommand):
    help="Measure warm local application processing for a public ranking view."
    def add_arguments(self,parser): parser.add_argument("--samples",type=int,default=50); parser.add_argument("--path",default="/rankings/attackers/")
    def handle(self,*args,**options):
        if options["samples"]<20: raise CommandError("Use at least 20 samples for a meaningful p95")
        client=Client(); timings=[]
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            response=client.get(options["path"])
            if response.status_code!=200: raise CommandError(f"Warmup returned HTTP {response.status_code}")
            for _ in range(options["samples"]):
                start=perf_counter(); response=client.get(options["path"]); timings.append((perf_counter()-start)*1000)
        p95=quantiles(timings,n=100,method="inclusive")[94]
        self.stdout.write(f"samples={len(timings)} min_ms={min(timings):.2f} mean_ms={sum(timings)/len(timings):.2f} p95_ms={p95:.2f} max_ms={max(timings):.2f}")
        if p95>=100: raise CommandError("Warm-cache p95 exceeds the 100 ms MVP target")
