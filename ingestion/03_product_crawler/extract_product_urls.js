const host = process.env.VM_EXTERNAL_IP || "localhost";
db = connect(`mongodb://${host}:27017/countly`);

print("Starting aggregation...");

db.summary.aggregate([
  { $match: {
    collection: { $in: [
      "view_product_detail",
      "select_product_option",
      "select_product_option_quality",
      "add_to_cart_action",
      "product_detail_recommendation_visible",
      "product_detail_recommendation_noticed",
      "product_view_all_recommend_clicked"
    ]}
  }},
  { $project: {
    product_id: {
      $cond: {
        if: { $eq: ["$collection", "product_view_all_recommend_clicked"] },
        then: "$viewing_product_id",
        else: "$product_id"
      }
    },
    url: {
      $cond: {
        if: { $eq: ["$collection", "product_view_all_recommend_clicked"] },
        then: "$referrer_url",
        else: "$current_url"
      }
    }
  }},
  { $group: {
    _id: "$product_id",
    url: { $first: "$url" }
  }},
  { $project: {
    _id: 0,
    product_id: "$_id",
    url: 1
  }},
  { $out: "product_urls" }
]);

print("Done! Count: " + db.product_urls.countDocuments());
print("Sample:");
printjson(db.product_urls.findOne());
