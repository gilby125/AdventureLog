import os
from .models import Adventure, AdventureImage, ChecklistItem, Collection, Note, Transportation, Checklist
from rest_framework import serializers

class AdventureImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureImage
        fields = ['id', 'image', 'adventure']
        read_only_fields = ['id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.image:
            public_url = os.environ.get('PUBLIC_URL', 'http://127.0.0.1:8000').rstrip('/')
            #print(public_url)
            # remove any  ' from the url
            public_url = public_url.replace("'", "")
            representation['image'] = f"{public_url}/media/{instance.image.name}"
        return representation


                                        
class AdventureSerializer(serializers.ModelSerializer):
    images = AdventureImageSerializer(many=True, read_only=True)
    class Meta:
        model = Adventure
        fields = ['id', 'user_id', 'name', 'description', 'rating', 'activity_types', 'location', 'date', 'is_public', 'collection', 'created_at', 'updated_at', 'images', 'link', 'type', 'longitude', 'latitude', 'end_date']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return representation
    
class TransportationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Transportation
        fields = [
            'id', 'user_id', 'type', 'name', 'description', 'rating', 
            'link', 'date', 'flight_number', 'from_location', 'to_location', 
            'is_public', 'collection', 'created_at', 'updated_at', 'end_date'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']

class NoteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Note
        fields = [
            'id', 'user_id', 'name', 'content', 'date', 'links', 
            'is_public', 'collection', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']
    
class ChecklistItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = ChecklistItem
            fields = [
                'id', 'user_id', 'name', 'is_checked', 'checklist', 'created_at', 'updated_at'
            ]
            read_only_fields = ['id', 'created_at', 'updated_at', 'user_id', 'checklist']
    
        # def validate(self, data):
        #     # Check if the checklist is public and the checklist item is not
        #     checklist = data.get('checklist')
        #     is_checked = data.get('is_checked', False)
        #     if checklist and checklist.is_public and not is_checked:
        #         raise serializers.ValidationError(
        #             'Checklist items associated with a public checklist must be checked.'
        #         )

    
class ChecklistSerializer(serializers.ModelSerializer):
    items = ChecklistItemSerializer(many=True, source='checklistitem_set')
    class Meta:
        model = Checklist
        fields = [
            'id', 'user_id', 'name', 'date', 'is_public', 'collection', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']
    
    def create(self, validated_data):
        items_data = validated_data.pop('checklistitem_set')
        checklist = Checklist.objects.create(**validated_data)
        for item_data in items_data:
            ChecklistItem.objects.create(checklist=checklist, **item_data)
        return checklist
    
    def update(self, instance, validated_data):
        items_data = validated_data.pop('checklistitem_set', [])
        
        # Update Checklist fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Get current items
        current_items = instance.checklistitem_set.all()
        current_item_ids = set(current_items.values_list('id', flat=True))
        
        # Update or create items
        updated_item_ids = set()
        for item_data in items_data:
            item_id = item_data.get('id')
            if item_id:
                if item_id in current_item_ids:
                    item = current_items.get(id=item_id)
                    for attr, value in item_data.items():
                        setattr(item, attr, value)
                    item.save()
                    updated_item_ids.add(item_id)
                else:
                    # If ID is provided but doesn't exist, create new item
                    ChecklistItem.objects.create(checklist=instance, **item_data)
            else:
                # If no ID is provided, create new item
                ChecklistItem.objects.create(checklist=instance, **item_data)
        
        # Delete items that are not in the updated data
        items_to_delete = current_item_ids - updated_item_ids
        instance.checklistitem_set.filter(id__in=items_to_delete).delete()
        
        return instance

    def validate(self, data):
        # Check if the collection is public and the checklist is not
        collection = data.get('collection')
        is_public = data.get('is_public', False)
        if collection and collection.is_public and not is_public:
            raise serializers.ValidationError(
                'Checklists associated with a public collection must be public.'
            )

        return data

   


class CollectionSerializer(serializers.ModelSerializer):
    adventures = AdventureSerializer(many=True, read_only=True, source='adventure_set')
    transportations = TransportationSerializer(many=True, read_only=True, source='transportation_set')
    notes = NoteSerializer(many=True, read_only=True, source='note_set')
    checklists = ChecklistSerializer(many=True, read_only=True, source='checklist_set')

    class Meta:
        model = Collection
        # fields are all plus the adventures field
        fields = ['id', 'description', 'user_id', 'name', 'is_public', 'adventures', 'created_at', 'start_date', 'end_date', 'transportations', 'notes', 'updated_at', 'checklists', 'is_archived', 'shared_with']
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Make it display the user uuid for the shared users instead of the PK
        shared_uuids = []
        for user in instance.shared_with.all():
            shared_uuids.append(str(user.uuid))
        representation['shared_with'] = shared_uuids
        return representation