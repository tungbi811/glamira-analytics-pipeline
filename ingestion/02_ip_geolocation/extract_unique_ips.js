db.summary.aggregate([
  { $group: { _id: "$ip" } },
  { $project: { _id: 0, ip: "$_id" } },
  { $out: "unique_ips" }
])

print("Done! Count: " + db.unique_ips.countDocuments());
