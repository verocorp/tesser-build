from __future__ import annotations

import tesser.adapters as ts

import parcel.application.ports as ports


class ParcelWireGateway(ts.Gateway):

    def manifest_parcel(
        self, manifest_parcel_request: ports.ManifestParcelRequest
    ) -> ports.ManifestParcelResponse:
        return ports.ManifestParcelResponse(
            parcel=ports.Parcel(
                parcel_code=manifest_parcel_request.code,
                item_count=manifest_parcel_request.items,
                weight_kg=manifest_parcel_request.weight_kg,
                label_digest_hex=manifest_parcel_request.label_digest.hex(),
                declared_value=manifest_parcel_request.declared_value,
                scanned_at=manifest_parcel_request.scanned_at,
                weight_class=manifest_parcel_request.weight_class,
            )
        )
