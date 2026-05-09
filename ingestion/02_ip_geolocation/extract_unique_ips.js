// DB_HOST is loaded from .env by the caller
const host = process.env.VM_EXTERNAL_IP || "localhost";
db = connect(`mongodb://${host}:27017/countly`);

db.summary.aggregate([
  { $group: { _id: "$ip"}},
  { $project: { _id: 0, ip: "$_id"}},
  { $out: "unique_ips"}
])

print("Done! Count: " + db.unique_ips.countDocuments());
