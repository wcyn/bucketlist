import ast

from flask import json
from flask import jsonify, request
from flask_jwt import jwt_required, current_identity
from flask_restful import Api, Resource, reqparse, abort, marshal_with
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError, validates
from marshmallow import fields
from marshmallow import post_dump
from marshmallow import post_load
from marshmallow import pre_dump
from marshmallow import pre_load

from api import db
from api.message_formatter import ErrorFormatter
from api.models import Bucketlist, BucketlistItem, Tag
from api.v1.auth.views import UserSchema
from . import bucketlists

api = Api(bucketlists)
ma = Marshmallow(bucketlists)
msg = ErrorFormatter()


def is_valid_json(data):
    try:
        json.dumps(data)
        json.loads(data)
    except ValueError:
        return False
    return True


def check_user_permission(user):
    if user != current_identity:
        abort(403, message="Forbidden. You may not view this data")
    return True


def abort_if_bucketlist_doesnt_exist(bucketlist_id):
    bucketlist = Bucketlist.get_bucketlist(bucketlist_id)
    if not bucketlist:
        abort(404, message="Bucketlist '{}' does not exist".format(
            bucketlist_id))
    elif check_user_permission(bucketlist.user):
        return bucketlist


def abort_if_bucketlist_item_doesnt_exist(bucketlist_item_id):
    bucketlist_item = BucketlistItem.get_bucketlist_item(bucketlist_item_id)
    if not bucketlist_item:
        abort(404, message="Bucketlist item '{}' does not exist".format(
            bucketlist_item_id
        ))
    elif check_user_permission(bucketlist_item.bucketlist.user):
        print("Abort not exist:", bucketlist_item, bucketlist_item.__dict__)
        return bucketlist_item


def abort_if_tag_doesnt_exist(tag_id):
    tag = Tag.get_tag(tag_id)
    if not tag:
        abort(404, message="Tag '{}' does not exist".format(
            tag_id
        ))
    elif check_user_permission(tag.user):
        return tag


class BucketlistSchema(ma.Schema):
    """
    Schema used to validate and serialize bucketlist data
    """
    id = fields.Integer(required=True, dump_only=True)
    description = fields.Str(required=True,
                             error_messages={
                               'required': 'Description is required.'})
    user = fields.Nested(UserSchema, exclude=('password', '_links', 'email'),
                         dump_only=True, required=True)
    item_count = fields.Function(lambda obj: obj.get_item_count())
    _links = ma.Hyperlinks({
        'self': ma.URLFor('bucketlists.bucketlists', id='<id>'),
        'collection': ma.URLFor('bucketlists.bucketlists')
    }, dump_only=True)

    @staticmethod
    def editable_fields():
        return ['description']

    @post_load
    def make_bucketlist(self, data):
        data['user'] = current_identity
        return Bucketlist(**data)

    @validates('description')
    def validate_description(self, description):
        if len(description) > 100:
            raise ValidationError(
                'Description cannot have more than 100 characters.',
                field_names=['description'], fields=['description'])
        elif len(description) < 1:
            raise ValidationError(
                'Description cannot be empty.',
                field_names=['description'], fields=['description'])

    @post_dump
    def fix_bucket_link(self, data):
        # print("Predump!!", data)
        # data['item_count'] = len(data['items'])
        data['_links']['self'] = data['_links']['collection'] + str(data['id'])
        return data


class TagSchema(ma.Schema):
    """
    Schema used to validate and serialize tag data
    """
    id = fields.Integer(required=True, dump_only=True)
    name = fields.Str(required=True,
                      error_messages={
                               'required': 'The tag name is required.'})
    user = fields.Nested(UserSchema, only='username',
                         dump_only=True, required=True)
    _links = ma.Hyperlinks({
        'self': ma.URLFor('bucketlists.tags', id='<id>'),
        'collection': ma.URLFor('bucketlists.tags')
    }, dump_only=True)

    @staticmethod
    def editable_fields():
        return ['name']

    @post_load
    def make_tag(self, data):
        data['user'] = current_identity
        return Tag(**data)

    @validates('name')
    def validate_description(self, name):
        if len(name) > 100:
            raise ValidationError(
                'Tag name cannot have more than 20 characters.',
                field_names=['name'], fields=['name'])
        elif len(name) < 1:
            raise ValidationError(
                'Tag name cannot be empty.',
                field_names=['name'], fields=['name'])

    @post_dump
    def fix_tag_link(self, data):
        if '_links' in data:
            data['_links']['self'] = data['_links']['collection'] +\
                                 "/" + str(data['id'])
        return data


class BucketlistItemSchema(ma.Schema):
    """
    Schema used to validate and serialize bucketlist item data
    """
    id = fields.Integer(required=True, dump_only=True)
    bucketlist_id = fields.Integer(required=True, dump_only=True)
    description = fields.Str(required=True,
                             error_messages={
                               'required': 'Description is required.'})
    done = fields.Boolean(truthy=['t', 'T', 'true', 'True', 'TRUE', '1', 1,
                                  True])
    tags = fields.Nested(TagSchema, many=True, only=["name", "id"])
    # Smart hyperlinking
    _links = ma.Hyperlinks({
        'self': ma.URLFor('bucketlists.bucketlists',
                          bucketlist_id='<bucketlist_id>', id='<id>'),
        'collection': ma.URLFor('bucketlists.bucketlists', id='<id>')
    })

    @validates('description')
    def validate_description(self, description):
        if len(description) > 300:
            raise ValidationError(
                'Description cannot have more than 300 characters.',
                field_names=['description'], fields=['description'])
        elif len(description) < 1:
            raise ValidationError(
                'Description cannot be empty.',
                field_names=['description'], fields=['description'])

    @post_dump
    def fix_bucket_item_link(self, data):
        print("\n\n Post dump bucketlist item: ", data)
        if '_links' in data:
            data['_links']['collection'] = '/'.join(
            data['_links']['collection'].split('/')[:-1]) + '/' + str(
            data['bucketlist_id'])
            data['_links']['self'] = data['_links'][
                                     'collection'] + '/' + str(data['id'])
        return data

    @post_load
    def get_bucketlist_item(self, data):
        print("\n\n Post load bucketlist item: ", data)

        with db.session.no_autoflush:
            bucketlist_item = BucketlistItem(**data)
            print("BUcketlist Item Load after: ", bucketlist_item.__dict__)
            return bucketlist_item

    @pre_load
    def check_tag_input(self, data):
        if 'tags' in data:
            tags = data['tags']
            for tag in tags:
                try:
                    tag_eval = ast.literal_eval(str(tag))
                    if not isinstance(tag_eval, dict):
                        raise ValidationError(
                        'Tags must be valid json', field_names=['tags'], fields=[
                            'tags'])
                except (ValueError, ):
                    raise ValidationError(
                        'Tags must be valid json', field_names=['tags'], fields=[
                            'tags'])
        return data

    @staticmethod
    def editable_fields():
        return ['description', 'done']


class BucketlistDetailsSchema(BucketlistSchema):
    items = fields.Nested(BucketlistItemSchema,
                          many=True)

bucketlist_schema = BucketlistSchema()
bucketlists_schema = BucketlistSchema(many=True)
bucketlist_details_schema = BucketlistDetailsSchema()
bucketlist_item_schema = BucketlistItemSchema()
bucketlist_items_schema = BucketlistItemSchema(many=True)
tag_schema = TagSchema()
tags_schema = TagSchema(many=True)


class Bucketlists(Resource):
    method_decorators = [jwt_required()]

    @staticmethod
    def get():
        """
        Get a list of bucketlists from the database
        :return:
        :rtype:
        """
        bucket_lists = Bucketlist.query.filter_by(
            user=current_identity).all()
        return bucketlists_schema.dump(bucket_lists)

    @staticmethod
    def post():
        """
        Add a new bucketlist to the database
        :return:
        :rtype:
        """
        post_data = json.loads(request.data.decode())
        bucketlist, error = bucketlist_schema.load(post_data)
        print("bucketlist: ", bucketlist.__dict__)
        if error:
            return msg.format_field_errors(error)
        bucketlist = bucketlist.create_bucketlist()
        if isinstance(bucketlist, Bucketlist):
            bucketlist_data, error = bucketlist_schema.dump(bucketlist)
            if error:
                return msg.format_field_errors(error)
            return bucketlist_data, 201
        return msg.format_general_errors(
            "An error occurred while creating the bucketlist")


class BucketlistDetails(Resource):
    method_decorators = [jwt_required()]

    @staticmethod
    def get(id):
        """
        Get the bucketlist with the specified id
        :param id: Bucketlist id from url
        :type id: integer
        :return: Data containing the updated bucketlist or an error message
        :rtype: JSON
        """
        bucketlist = abort_if_bucketlist_doesnt_exist(id)
        return bucketlist_details_schema.dump(bucketlist)

    @staticmethod
    def put(id):
        """
        Update the bucketlist with the specified id
        :param id: Bucketlist id from url
        :type id: integer
        :return: Data containing the updated bucketlist or an error message
        :rtype: JSON
        """
        bucketlist = abort_if_bucketlist_doesnt_exist(id)
        put_data = json.loads(request.data.decode())
        put_data['id'] = id
        data, error = bucketlist_schema.dump(put_data)
        if error:
            return msg.format_field_errors(error)
        bucketlist_obj, error = bucketlist_schema.load(put_data)
        if error:
            return msg.format_field_errors(error)
        for key, value in bucketlist_obj.__dict__.items():
            if key in bucketlist_schema.editable_fields():
                setattr(bucketlist, key, value)
        bucketlist = bucketlist.update_bucketlist()
        if isinstance(bucketlist, Bucketlist):
            bucketlist_data, error = bucketlist_schema.dump(bucketlist)
            if error:
                return msg.format_field_errors(error)
            return bucketlist_data, 201
        return msg.format_general_errors(
            "An error occurred while updating the bucketlist")

    @staticmethod
    def post(id):
        """
        Add a new Bucketlist Item to the bucketlist with specified id, to the
        database
        :param id: Bucketlist id from url
        :type id: integer
        :return: Data containing the newly created bucketlist item or an
        error message
        :rtype: JSON
        """
        post_data = json.loads(request.data.decode())
        # print("Request decoded two: ", post_data, type(post_data))
        print("post item data: ", post_data)
        bucketlist_item, error = bucketlist_item_schema.load(post_data)
        if error:
            return msg.format_field_errors(error)
        print("\n\n yu bucketlistitem: ", bucketlist_item)

        bucketlist_item = bucketlist_item.create_bucketlist_item(id)
        if isinstance(bucketlist_item, BucketlistItem):
            print("\n\n && Valid bitem instance? ", bucketlist_item)
            bucketlist_item_data, error = bucketlist_item_schema.dump(
                bucketlist_item)
            if error:
                return msg.format_field_errors(error)
            return bucketlist_item_data, 201
        return msg.format_general_errors(
            "An error occurred while creating the bucketlist")

    @staticmethod
    def delete(id):
        bucketlist = abort_if_bucketlist_doesnt_exist(id)
        bucketlist.delete_bucketlist()
        return msg.format_success_message(
            "Bucketlist successfully deleted", 200)


class BucketlistItemDetails(Resource):
    method_decorators = [jwt_required()]

    @staticmethod
    def get(id, item_id):
        abort_if_bucketlist_doesnt_exist(id)
        abort_if_bucketlist_item_doesnt_exist(item_id)
        bucket_list_items = BucketlistItem.query.filter_by(
            bucketlist_id=id, id=item_id).first()
        return bucketlist_item_schema.dump(bucket_list_items)

    @staticmethod
    def put(id, item_id):
        abort_if_bucketlist_doesnt_exist(id)
        bucketlist_item = abort_if_bucketlist_item_doesnt_exist(item_id)
        print("\n\n 1. gjh Before Updating BIT:...:", "\n\n",
              bucketlist_item.__dict__)
        put_data = json.loads(request.data.decode())
        put_data['id'] = item_id
        put_data['bucketlist_id'] = id
        data, error = bucketlist_item_schema.dump(put_data)
        if error:
            return msg.format_field_errors(error)
        # Load so as to validate
        bucketlist_item_object, error = bucketlist_item_schema.load(put_data)
        print("\n\n 3. gjh Before Updating BIT:...:", "\n\n",
              bucketlist_item.__dict__)
        print("\n\n\nLoaded BITEM: ", bucketlist_item_object.__dict__)
        if error:
            return msg.format_field_errors(error)
        print("\n\n gjh Before Updating BIT:...:", bucketlist_item_object.__dict__, "\n\n", bucketlist_item.__dict__)
        for key, value in bucketlist_item_object.__dict__.items():
            if key in bucketlist_item_schema.editable_fields():
                print("Updating BIT:...", bucketlist_item.__dict__)
                setattr(bucketlist_item, key, value)

        print("Final Updating BIT:...", bucketlist_item.__dict__)
        bucketlist_item = bucketlist_item.update_bucketlist_item(bucketlist_item_object.tags)
        if isinstance(bucketlist_item, BucketlistItem):
            bucketlist_item_data, error = bucketlist_item_schema.dump(
                bucketlist_item)
            if error:
                return msg.format_field_errors(error)
            return bucketlist_item_data, 201
        return msg.format_general_errors(
            "An error occurred while updating the bucketlist")

    @staticmethod
    def delete(id, item_id):
        abort_if_bucketlist_doesnt_exist(id)
        bucketlist_item = abort_if_bucketlist_item_doesnt_exist(item_id)
        bucketlist_item.delete_bucketlist_item()
        return msg.format_success_message(
            "Bucketlist item successfully deleted", 200)


class TagDetails(Resource):
    method_decorators = [jwt_required()]

    @staticmethod
    def get(id):
        tag = abort_if_tag_doesnt_exist(id)
        return tag_schema.dump(tag)

    @staticmethod
    def put(id):
        tag = abort_if_tag_doesnt_exist(id)
        put_data = json.loads(request.data.decode())
        data, error = tag_schema.dump(put_data)
        if error:
            return msg.format_field_errors(error)
        # Load so as to validate
        tag_object, error = tag_schema.load(put_data)
        if error:
            return msg.format_field_errors(error)
        for key, value in tag_object.__dict__.items():
            if key in tag_schema.editable_fields():
                setattr(tag, key, value)
        tag = tag.update_tag()
        if isinstance(tag, Tag):
            tag_data, error = tag_schema.dump(
                tag)
            if error:
                return msg.format_field_errors(error)
            return tag_data, 201
        return msg.format_general_errors(
            "An error occurred while updating the tag")

    @staticmethod
    def delete(id):
        tag = abort_if_tag_doesnt_exist(id)
        tag.delete_tag_item()
        return msg.format_success_message(
            "Tag item successfully deleted", 200)


class Tags(Resource):
    method_decorators = [jwt_required()]

    @staticmethod
    def get():
        """
        Get a list of tags from the database
        :return:
        :rtype:
        """
        tags = Tag.query.filter_by(
            id=1).all()
        return tags_schema.dump(tags)

    @staticmethod
    def post():
        """
        Add a new tag to the database
        :return:
        :rtype:
        """
        post_data = json.loads(request.data.decode())
        # print("Request decoded two: ", post_data, type(post_data))
        tag, error = tag_schema.load(post_data)
        print("tag: ", tag.__dict__)
        if error:
            return msg.format_field_errors(error)
        tag = tag.create_tag()
        if isinstance(tag, Tag):
            tag_data, error = tag_schema.dump(tag)
            if error:
                return msg.format_field_errors(error)
            return tag_data, 201
        return msg.format_general_errors(
            "An error occurred while creating the tag")


api.add_resource(Bucketlists, '/')
api.add_resource(Tags, '/tags')
api.add_resource(TagDetails, '/tags/<int:id>')
api.add_resource(BucketlistDetails, '/<int:id>')
api.add_resource(BucketlistItemDetails, '/<int:id>/<int:item_id>')
