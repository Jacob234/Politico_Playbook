{
    "$schema": "http://json-schema.org/draft-04/schema#",
    "$id": "https://example.com/employee.schema.json",
    "title": "Newsletter",
    "description": "This document records a cleaned version a newsletter in json format",
    "type": "object",
    "properties": {
        "file_name": {
            "type": "string",
            "description": "The name of the file"
        },
        
        "date": {
            "type": "string",
            "format": "date",
            "description": "The date of the newsletter"
        },

        "subject_line": {
            "type": "string",
            "description": "The subject line of the newsletter"
        },
        
        "playbook_type": {
            "type": "string",
            "description": "The category of playbook"
        },
        
        "authors": {
            "type": "array",
            "items": {
                "type": "string"
            },
            "description": "List of authors who contributed to the newsletter. Could be a singleton"
        },
        "sponsor": {
            "type": "string",
            "description": "The presented by"
        },
        "text": {
            "type": "string",
            "description": "The text of the newsletter"
        }
    }
}