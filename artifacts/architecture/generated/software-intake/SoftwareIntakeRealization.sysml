// Generated fragment inserted into SoftwareIntake by the builder; do not edit.
package Reference {
  doc /* Selected software and virtual resources from IaC. Tiers and zones are explanatory classifications, not containing systems. Physical identities remain site-owned. */
  part <'R-Pair'> services : PolicyProxy {
    part <'VM-cache-1'> 'cache-1' : ProxyMember {
      attribute selectedNetwork : ScalarValues::String = "external_edge";
      part <'RUN-cache-1'> proxy :>> ProxyMember::proxy;
      part <'DISK-cache-1'> storage :>> ProxyMember::storage {
        item <'CONTENT-cache-1'> 'Cached content' :>> DisposableCache::contents;
      }
      flow <'IO-cache-1'> cacheIO from proxy.cacheAccess.payload to storage.access.payload;
    }
    part <'VM-cache-2'> 'cache-2' : ProxyMember {
      attribute selectedNetwork : ScalarValues::String = "external_edge";
      part <'RUN-cache-2'> proxy :>> ProxyMember::proxy;
      part <'DISK-cache-2'> storage :>> ProxyMember::storage {
        item <'CONTENT-cache-2'> 'Cached content' :>> DisposableCache::contents;
      }
      flow <'IO-cache-2'> cacheIO from proxy.cacheAccess.payload to storage.access.payload;
    }
  }
  part <'R-VIP'> vip : SharedListener;
  flow <'R-dispatch'> dispatch from vip.dispatch.payload to services.listener.payload;
  ref part <'R-Upstream'> sources : ApprovedSource;
  ref part <'R-Consumers'> clients : UpdateClient;
  flow <'R-request'> request from clients.access.payload to vip.inbound.payload;
  flow <'R-upstream'> upstream from services.outbound.payload to sources.access.payload;
  allocation <'ALLOC-proxy'> allocate context.'Policy proxy / HTTP cache' to services;
  allocation <'ALLOC-cache-1'> allocate context.'Rebuildable cache storage' to services.'cache-1'.storage;
  dependency <'HOST-cache-1'> 'Uses virtual execution: cache-1' from services::'cache-1' to platform::'Proxmox virtualization';
  dependency <'NET-cache-1'> 'Uses guest attachment: cache-1' from services::'cache-1' to platform::'Guest network attachment';
  dependency <'STORE-cache-1'> 'Uses local storage: cache-1' from services::'cache-1'::storage to platform::'Local guest-disk service';
  allocation <'ALLOC-cache-2'> allocate context.'Rebuildable cache storage' to services.'cache-2'.storage;
  dependency <'HOST-cache-2'> 'Uses virtual execution: cache-2' from services::'cache-2' to platform::'Proxmox virtualization';
  dependency <'NET-cache-2'> 'Uses guest attachment: cache-2' from services::'cache-2' to platform::'Guest network attachment';
  dependency <'STORE-cache-2'> 'Uses local storage: cache-2' from services::'cache-2'::storage to platform::'Local guest-disk service';
}
