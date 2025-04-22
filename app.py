import streamlit as st
import datetime
import json
from rubicon_cs.main import geotiff_for_veg_index
import os
import rasterio
import matplotlib.pyplot as plt
import io
from PIL import Image

# Imprimer tous les secrets pour voir leur structure
st.write("Tous les secrets :", st.secrets)

# Vérifier un secret spécifique
client_id = st.secrets["general"]["SH_CLIENT_ID"]
client_secret = st.secrets["general"]["SH_CLIENT_SECRET"]

st.write(f"Client ID : {client_id}")
st.write(f"Client Secret : {client_secret}")

def display_geotiff_streamlit(tiff_path, ncols=2, cmap='Greens', ):
    """
    Affiche les bandes d’un fichier GeoTIFF dans Streamlit.

    Paramètres :
        tiff_path (str) : chemin du fichier GeoTIFF
        ncols (int) : nombre de colonnes dans l’affichage en grille
        cmap (str) : colormap Matplotlib
    """
    with rasterio.open(tiff_path) as tiff:
        nrows = (tiff.count // ncols) + (1 if tiff.count % ncols != 0 else 0)

        fig, ax = plt.subplots(ncols=ncols, nrows=nrows, figsize=(10, 5 * nrows))
        axes = ax.flatten() if tiff.count > 1 else [ax]

        for i in range(tiff.count):
            band_data = tiff.read(i + 1)

            # Metadata date
            band_metadata = tiff.tags(i + 1)
            acquisition_date = band_metadata.get("DATE", "Date inconnue")

            im = axes[i].imshow(band_data, cmap=cmap, vmin=-1, vmax=1)
            axes[i].set_title(f"{tiff_path.split('.tif')[-2].split('_')[-1].upper()} Index in AOI on {acquisition_date}", fontsize=10)
            axes[i].axis("off")
            fig.colorbar(im, ax=axes[i], orientation='horizontal', shrink=0.7, pad=0.05)

        for j in range(tiff.count, len(axes)):
            axes[j].axis("off")  # désactive les cases en trop

        plt.tight_layout()

        # Sauvegarde de la figure dans un buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1)
        buf.seek(0)
        image = Image.open(buf)
        st.image(image, caption="Aperçu des bandes du GeoTIFF", use_container_width=True)
        plt.close(fig)


st.set_page_config(page_title="Sélection des paramètres", layout="centered")

st.title("🌿 Sélection des paramètres d'analyse")

# Dates
st.subheader("🗓️ Période d’analyse")
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("Date de début", datetime.date(2024, 8, 20))
with col2:
    end_date = st.date_input("Date de fin", datetime.date(2024, 9, 10))

# Index
st.subheader("📈 Choix de l’indice de végétation")
index_options = ["NDVI", "EVI", "SAVI", "GNDVI", "NDRE","ARVI" ]
selected_index = st.selectbox("Indice de végétation", index_options)

# Couverture nuageuse
st.subheader("☁️ Limite de couverture nuageuse")
cloud_coverage = st.slider("Pourcentage max de nuages (%)", min_value=0, max_value=100, value=20)

# Upload AOI
st.subheader("📍 Zone d’étude (AOI.geojson)")
uploaded_file = st.file_uploader("Importer un fichier .geojson", type=["geojson"])

if uploaded_file:
    try:
        geojson_data = json.load(uploaded_file)["features"][0]["geometry"]
        st.success("✅ AOI chargé avec succès !")
    except Exception as e:
        st.error(f"Erreur lors du chargement : {e}")

# Traitement
if st.button("🚀 Lancer l’analyse") and geojson_data:
    st.info("Traitement en cours...")
    with st.spinner("Génération du GeoTIFF..."):
        geotiff_for_veg_index(
            AOI=geojson_data,
            date_range=(start_date, end_date),
            veg_index=selected_index.lower(),
            cloud_cover_limit=cloud_coverage,
            output_dir = 'app_outputs/section_1'
        )

        # Chemin attendu du GeoTIFF généré
        tif_path = f'app_outputs/section_1/{start_date}_{end_date}_{selected_index.lower()}.tif'

        if os.path.exists(tif_path):
            st.success("✅ GeoTIFF généré avec succès !")

            # Affichage
            st.subheader("🖼️ Aperçu du rendu")
            with st.spinner("Génération du rendu..."):
                display_geotiff_streamlit(tif_path, ncols=1, cmap='Greens')

            # Téléchargement
            with open(tif_path, "rb") as file:
                st.download_button(
                    label="💾 Télécharger le GeoTIFF",
                    data=file,
                    file_name=os.path.basename(tif_path),
                    mime="application/octet-stream"
                )
        else:
            st.error("❌ Le fichier GeoTIFF n’a pas été trouvé.")
