"""Kubernetes API collector merging all resource data."""

from typing import Dict, Any, List
from kubernetes import client, config as k8s_config

from .base import BaseCollector

class KubernetesAPICollector(BaseCollector):
    """Collects events and merges observability data per resource."""

    RESOURCE_TYPES = ["pod", "node", "deployment", "statefulset",
                      "daemonset", "service", "ingress", "configmap"]

    def __init__(self, cfg: Dict[str, Any]):
        super().__init__(cfg)
        try:
            # Try in-cluster configuration first (when running in Kubernetes)
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()
        except:
            # Fall back to kubeconfig if in-cluster config fails (when running locally)
            k8s_config.load_kube_config()
            self.v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.networking_v1 = client.NetworkingV1Api()

    def collect(self) -> Dict[str, Any]:
        events = self._collect_events()
        resources = self.merge_observability_data(events)
        return resources

    def _collect_events(self) -> List[Dict]:
        all_events = []
        for ns in [ns.metadata.name for ns in self.v1.list_namespace().items]:
            evts = self.v1.list_namespaced_event(ns)
            for e in evts.items:
                all_events.append(e.to_dict())
        return all_events

    def merge_observability_data(self, events: List[Dict]) -> Dict[str, Any]:
        data: Dict[str, Any] = {rtype: {} for rtype in self.RESOURCE_TYPES}
        for evt in events:
            rtype = evt.get("involved_object", {}).get("kind", "").lower()
            rname = evt.get("involved_object", {}).get("name")
            if rtype in data and rname:
                data[rtype].setdefault(rname, {"events": [], "logs": [], "traces": [], "metrics": {}})
                data[rtype][rname]["events"].append(evt)
        return data