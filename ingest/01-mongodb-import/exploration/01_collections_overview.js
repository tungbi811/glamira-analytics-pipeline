num_documents = db.summary.countDocuments()
print("Total documents:", num_documents)

print("\n--- Sample Documents ---")
printjson(db.summary.findOne())