<template>
  <div class="home">
    <h1>Welcome to Music To Partition</h1>
    <!-- Upload section -->
    <div class="upload-section">
      <label for="fileUpload">Upload the music you want to convert into a partition here :</label>
      <input type="file" id="fileUpload" accept=".wav,.mp3,.aac,.m4a" @change="handleFileUpload"/>
    </div>

    <!-- Analysis -->
    <button @click="onAnalyse" :disabled="!selectedFile">
      Launch Partition generation
    </button>

    <!-- Analysis indicator -->
     <div v-if="analysisInProgress" class="analysis-status">
      <p>Generation incoming...</p>
     </div>

     <!-- List of generated partitions -->
      <div v-if="partitions.length > 0" class='partitions-list'>
        <h2>Generated partitions</h2>
        <ul>
          <li v-for="(partition, index) in partitions" :key="index"
              class="partition-item">
            <!-- <PdfThumbnail :pdfSrc="partition.pdfSrc" :page="1"></PdfThumbnail> -->
            <div>
              <a
                :href="partition.pdfSrc"
                target="_blank"
                download>
                Partition {{ index + 1 }} ({{ partition.instrument }})
              </a>
            </div>
          </li>
        </ul>
      </div>
  </div>
</template>

<script>
// import PdfThumbnail from './PdfThumbnail.vue';
import axios from 'axios';

export default {
  name: 'Home',
  // components: {PdfThumbnail},
  data() {
    return {
      selectedFile: null,
      analysisInProgress: false,
      partitions: []
    }
  },
  methods: {
    handleFileUpload(event) {
      const file = event.target.files[0];
      console.log(event)
      if (file && (file.type === 'audio/x-wav' || file.type === 'audio/mpeg' || file.type === 'audio/mp3' || file.type === 'audio/aac' || file.type === 'audio/x-m4a')) {
        this.selectedFile = file;
      } else {
        alert('Veuillez sélectionner un fichier au format approprié (WAV, MP3, AAC ou M4A)');
        event.target.value = null;
        this.selectedFile = null;
      }
    },

    async onAnalyse() {
      this.analysisInProgress = true;

      try {
        // Data preparation
        const formData = new FormData();
        formData.append('file', this.selectedFile);

        // Call to FastAPI endpoint
        const response = await axios.post('http://localhost:8000/api/upload/', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        });

        // If everythhing is alright, we can  get back partitions sent by back-end
        this.partitions = response.data.partitions;
        console.log('Partitions reçues :', this.partitions);

      } catch(error) {
        console.log('Error during analysis :', error);
        alert('An error occured while uploading or while analysing.');
      } finally {
        this.analysisInProgress = false;
      }
    }
  }
}
</script>

<style scoped>
.home {
  text-align: center;
  margin-top: 50px;
}

.upload-section {
  margin-bottom: 20px;
}

.analysis-status {
  margin: 20px 0;
  font-style: italic;
}

.partitions-list {
  margin-top: 30px;
}

.partition-item {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 20px;
}

</style>
