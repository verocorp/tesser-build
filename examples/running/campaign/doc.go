// Package campaign holds the link-campaign domain: the Campaign aggregate,
// the ShortLink entity it owns, and their value objects (Slug, TargetURL,
// CampaignName, CampaignID). This is the innermost layer — it has no
// dependency on persistence, transport, or the public interface package;
// everything else in examples/running depends on it, never the reverse.
package campaign
