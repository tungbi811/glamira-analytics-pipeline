print("--- option field type distribution ---")
db.summary.aggregate([
    { $group: { _id: { $type: "$option" }, count: { $sum: 1 } } },
    { $sort: { count: -1 } }
]).forEach(doc => print(doc._id + ": " + doc.count))

print("\n--- option_label values (standard array format) ---")
db.summary.aggregate([
    { $match: { "option.option_label": { $exists: true } } },
    { $unwind: "$option" },
    { $group: { _id: "$option.option_label", count: { $sum: 1 } } },
    { $sort: { count: -1 } }
]).forEach(doc => print(doc._id + ": " + doc.count))