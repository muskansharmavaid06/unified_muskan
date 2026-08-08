from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score

def evaluate_kmeans(X, max_k=10):
    wcss = []
    silhouette_scores = []
    k_range = range(2, max_k + 1)
    
    for k in k_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)
        wcss.append(kmeans.inertia_)
        silhouette_scores.append(silhouette_score(X, kmeans.labels_))
        
    return k_range, wcss, silhouette_scores

def run_clustering(X, n_clusters=4, method='kmeans'):
    if method == 'kmeans':
        model = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    else:
        model = AgglomerativeClustering(n_clusters=n_clusters)
        
    cluster_labels = model.fit_predict(X)
    return cluster_labels