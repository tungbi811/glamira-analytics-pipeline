const result = db.summary.aggregate([
    { $project: { fields: { $objectToArray: "$$ROOT" } } },
    { $unwind: "$fields" },
    { $group: {
        _id: "$fields.k",
        types: { $addToSet: { $type: "$fields.v" } },
        not_null_count: { $sum: { $cond: [{ $in: [{ $type: "$fields.v" }, ["null", "missing"]] }, 0, 1] } },
        null_count: { $sum: { $cond: [{ $in: [{ $type: "$fields.v" }, ["null", "missing"]] }, 1, 0] } }
    }},
    { $project: { types: 1, not_null_count: 1, null_count: 1 } },
    { $sort: { _id: 1 } }
],
{ allowDiskUse: true })

result.forEach(doc => print(doc._id + " | types: " + doc.types + " | not_null: " + doc.not_null_count + " | null: " + doc.null_count))