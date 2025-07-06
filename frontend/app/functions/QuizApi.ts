import axios from "axios"
export function QuizAPi(formData:string){
    axios.post("http://localhost:8000/getQuiz", formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000,
      })
      .then((response) => {
        return response.data.summary;
      })
}