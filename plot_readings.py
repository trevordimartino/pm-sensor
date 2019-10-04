import firebase_admin
from firebase_admin import firestore
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
sns.set(style="whitegrid", context="talk")

# Credentials pulled from file named in GOOGLE_APPLICATION_CREDENTIALS os env var
app = firebase_admin.initialize_app()
db = firestore.client()

readings = db.collection(u'readings').order_by(u'time').stream()
values = [reading.to_dict() for reading in readings]

data = pd.DataFrame(values)

plt.figure()
sns.lineplot(x='time', y='pm10', data=data, linewidth=1)
sns.lineplot(x='time', y='pm2.5', data=data, linewidth=1)
sns.despine()
plt.show()
